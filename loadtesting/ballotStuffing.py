import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import requests
import json
import msgpack
from datetime import datetime

def get_election_by_id(election_id):
    """
    Retrieve election row by election_id
    
    Args:
        election_id (int): The election ID to search for
        
    Returns:
        dict: Election data as dictionary, or None if not found
    """
    try:
        connection = psycopg2.connect(
            database="amarvote_db",
            user="amarvote_user",
            password="amarvote_password",
            host="localhost",
            port="5432"
        )
        
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM elections WHERE election_id = %s"
        cursor.execute(query, (election_id,))
        
        election = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if election:
            return dict(election)
        else:
            print(f"No election found with ID: {election_id}")
            return None
            
    except Exception as error:
        print(f"Error retrieving election: {error}")
        return None


def get_election_choices(election_id):
    """
    Retrieve all choices (candidates) for a given election
    
    Args:
        election_id (int): The election ID
        
    Returns:
        list: List of choice dictionaries, or empty list if error
    """
    try:
        connection = psycopg2.connect(
            database="amarvote_db",
            user="amarvote_user",
            password="amarvote_password",
            host="localhost",
            port="5432"
        )
        
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM election_choices WHERE election_id = %s ORDER BY choice_id"
        cursor.execute(query, (election_id,))
        
        choices = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return [dict(choice) for choice in choices]
            
    except Exception as error:
        print(f"Error retrieving election choices: {error}")
        return []


def create_encrypted_ballot(ballot_data, api_url="http://localhost:5000/create_encrypted_ballot"):
    """
    Call the ElectionGuard API to create an encrypted ballot.

    The API accepts:
        party_names, candidate_names, candidate_name, ballot_id,
        joint_public_key, commitment_hash, number_of_guardians, quorum,
        ballot_status (optional, default 'CAST')

    The API returns:
        status, ballot_id, ballot_status, ballot_hash,
        encrypted_ballot (sanitized, no nonces),
        encrypted_ballot_with_nonce (full, with nonces - use for storage/tallying),
        publication_status

    Args:
        ballot_data (dict): Ballot data to send to API
        api_url (str): API endpoint URL

    Returns:
        dict: API response data, or None if error
    """
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(api_url, json=ballot_data, headers=headers, timeout=300)

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'msgpack' in content_type:
                return msgpack.unpackb(response.content, raw=False)
            else:
                # Fallback: try JSON, then msgpack
                try:
                    return response.json()
                except Exception:
                    return msgpack.unpackb(response.content, raw=False)
        else:
            print(f"API Error: Status {response.status_code}, Response: {response.text[:500]}")
            # Try to decode error body as msgpack for a cleaner message
            try:
                err = msgpack.unpackb(response.content, raw=False)
                print(f"API Error detail: {err}")
            except Exception:
                pass
            return None

    except Exception as error:
        print(f"Error calling API: {error}")
        return None


def add_ballot_to_db(election_id, ballot_id, ballot_hash, cipher_text, user_email):
    """
    Add ballot to database and update allowed_voters
    
    Args:
        election_id (int): The election ID
        ballot_id (str): Ballot tracking code
        ballot_hash (str): Hash of the ballot
        cipher_text (str): Encrypted ballot data
        user_email (str): Voter email
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        connection = psycopg2.connect(
            database="amarvote_db",
            user="amarvote_user",
            password="amarvote_password",
            host="localhost",
            port="5432"
        )
        
        cursor = connection.cursor()
        connection.autocommit = False
        
        # Insert ballot
        insert_ballot_query = """
        INSERT INTO ballots (election_id, cipher_text, hash_code, tracking_code, status)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_ballot_query, 
                      (election_id, cipher_text, ballot_hash, ballot_id, 'cast'))
        
        # Update allowed_voters
        update_voter_query = """
        UPDATE allowed_voters 
        SET has_voted = TRUE 
        WHERE election_id = %s AND user_email = %s
        """
        cursor.execute(update_voter_query, (election_id, user_email))
        
        # If voter doesn't exist, insert them
        if cursor.rowcount == 0:
            insert_voter_query = """
            INSERT INTO allowed_voters (election_id, user_email, has_voted)
            VALUES (%s, %s, TRUE)
            """
            cursor.execute(insert_voter_query, (election_id, user_email))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as error:
        connection.rollback()
        print(f"Error adding ballot to database: {error}")
        return False


def distribute_ballots_by_candidate(num_ballots, num_candidates):
    """
    Distribute ballot counts evenly across candidates
    
    Args:
        num_ballots (int): Total number of ballots
        num_candidates (int): Number of candidates
        
    Returns:
        list: List of ballot counts per candidate
    """
    base_count = num_ballots // num_candidates
    remainder = num_ballots % num_candidates
    
    distribution = [base_count] * num_candidates
    
    # Distribute remainder to last candidates
    for i in range(remainder):
        distribution[-(i+1)] += 1
    
    return distribution


def generate_ballots(election_id, num_ballots=1000):
    """
    Generate and insert ballots for an election
    
    Args:
        election_id (int): The election ID
        num_ballots (int): Number of ballots to generate (default: 1000)
    """
    print(f"Starting ballot generation for election {election_id}...")
    
    # Step 1: Fetch election information
    election = get_election_by_id(election_id)
    if not election:
        print("Failed to fetch election information. Exiting.")
        return
    
    print(f"Election: {election['election_title']}")
    print(f"Number of Guardians: {election['number_of_guardians']}")
    print(f"Quorum: {election['election_quorum']}")
    
    # Step 2: Fetch election choices
    choices = get_election_choices(election_id)
    if not choices:
        print("No choices found for this election. Exiting.")
        return
    
    num_candidates = len(choices)
    print(f"\nFound {num_candidates} candidates:")
    print(choices)
    # Extract party names and candidate names
    party_names = [choice.get('party_name', f"Party {i+1}") for i, choice in enumerate(choices)]
    print('party names ', party_names)
    candidate_names = [choice.get('option_title', f"Candidate {i+1}") for i, choice in enumerate(choices)]
    
    for i, name in enumerate(candidate_names):
        print(f"  {i+1}. {name} ({party_names[i]})")
    
    # Step 3: Distribute ballots across candidates
    distribution = distribute_ballots_by_candidate(num_ballots, num_candidates)
    print(f"\nBallot distribution: {distribution}")
    
    # Step 4: Generate and process ballots
    ballot_counter = 1
    success_count = 0
    fail_count = 0
    
    for candidate_idx, candidate_ballot_count in enumerate(distribution):
        candidate_name = candidate_names[candidate_idx]
        print(f"\nGenerating {candidate_ballot_count} ballots for {candidate_name}...")
        
        for i in range(candidate_ballot_count):
            ballot_id = f"ballot-{ballot_counter}"
            user_email = f"a{ballot_counter}@example.com"
            
            # Prepare API request payload
            payload = {
                "party_names": party_names,
                "candidate_names": candidate_names,
                "candidate_name": candidate_name,
                "ballot_id": ballot_id,
                "joint_public_key": election['joint_public_key'],
                "commitment_hash": election['base_hash'],
                "number_of_guardians": election['number_of_guardians'],
                "quorum": election['election_quorum']
            }
            
            print('payload:')
            with open('payload.json', 'w') as f:
                json.dump(payload,f)
            print(payload)
            # Call ElectionGuard API
            api_response = create_encrypted_ballot(payload)
            print('api response: ', api_response)
            if api_response and api_response.get('status') == 'success':
                # Extract response data
                # Use ballot_hash from the published ballot
                ballot_hash = api_response['ballot_hash']
                # Use encrypted_ballot_with_nonce for DB storage so the
                # tally/decryption services receive the full ciphertext.
                # Fall back to encrypted_ballot if the nonce field is absent.
                encrypted_ballot = (
                    api_response.get('encrypted_ballot_with_nonce')
                    or api_response['encrypted_ballot']
                )

                # Add to database
                success = add_ballot_to_db(
                    election_id=election_id,
                    ballot_id=ballot_id,
                    ballot_hash=ballot_hash,
                    cipher_text=encrypted_ballot,
                    user_email=user_email
                )
                
                if success:
                    success_count += 1
                    if ballot_counter % 100 == 0:
                        print(f"  Progress: {ballot_counter}/{num_ballots} ballots processed")
                else:
                    fail_count += 1
                    print(f"  Failed to add ballot {ballot_id} to database")
            else:
                fail_count += 1
                print(f"  Failed to encrypt ballot {ballot_id}")
            
            ballot_counter += 1
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Ballot Generation Complete!")
    print(f"{'='*50}")
    print(f"Total ballots requested: {num_ballots}")
    print(f"Successfully created: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Success rate: {(success_count/num_ballots)*100:.2f}%")


if __name__ == "__main__":
    # Set your election ID here
    ELECTION_ID = 1
    NUM_BALLOTS = 300
    
    generate_ballots(ELECTION_ID, NUM_BALLOTS)
