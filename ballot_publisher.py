"""
Integration script for secure ballot publication in ElectionGuard API.

This script provides the integration functions to be used in your main API
to handle ballot sanitization for cast vs audited ballots.
"""

import json
from typing import Dict, Any, Optional
from ballot_sanitizer import prepare_ballot_for_publication, process_ballot_response


class BallotPublisher:
    """
    Class to handle secure ballot publication for ElectionGuard API.
    """
    
    def __init__(self):
        self.cast_ballots = {}      # Store cast ballot data
        self.audited_ballots = {}   # Store audited ballot data
        self.ballot_nonces = {}     # Store nonces for audited ballots only
    
    def publish_ballot(self, ballot_id: str, encrypted_ballot_response: str, ballot_status: str) -> Dict[str, Any]:
        """
        Publish a ballot securely based on its status.
        
        Args:
            ballot_id: Unique identifier for the ballot
            encrypted_ballot_response: Complete JSON response from ballot encryption
            ballot_status: "CAST" or "AUDITED"
        
        Returns:
            Dictionary containing the publishable ballot data
        """
        if ballot_status.upper() not in ["CAST", "AUDITED"]:
            raise ValueError("ballot_status must be either 'CAST' or 'AUDITED'")
        
        try:
            # Process the ballot response for publication
            publication_data = process_ballot_response(encrypted_ballot_response, ballot_status)
            
            # Store the ballot based on status
            if ballot_status.upper() == "CAST":
                self.cast_ballots[ballot_id] = {
                    "ballot_id": ballot_id,
                    "status": "CAST",
                    "published_at": self._get_timestamp(),
                    "ballot_hash": publication_data["ballot_hash"],
                    "sanitized_ballot": publication_data["sanitized_encrypted_ballot"]
                    # NOTE: No nonces stored for cast ballots
                }
                
                # Return publishable data (without nonces)
                return {
                    "ballot_id": ballot_id,
                    "status": "CAST",
                    "ballot_hash": publication_data["ballot_hash"],
                    "encrypted_ballot": publication_data["sanitized_encrypted_ballot"],
                    "publication_status": "published_without_nonces"
                }
                
            else:  # AUDITED
                self.audited_ballots[ballot_id] = {
                    "ballot_id": ballot_id,
                    "status": "AUDITED", 
                    "published_at": self._get_timestamp(),
                    "ballot_hash": publication_data["ballot_hash"],
                    "sanitized_ballot": publication_data["sanitized_encrypted_ballot"]
                }
                
                # Store nonces separately for audited ballots
                self.ballot_nonces[ballot_id] = publication_data["nonces_to_reveal"]
                
                # Return publishable data (with nonces)
                return {
                    "ballot_id": ballot_id,
                    "status": "AUDITED",
                    "ballot_hash": publication_data["ballot_hash"],
                    "encrypted_ballot": publication_data["sanitized_encrypted_ballot"],
                    "ballot_nonces": publication_data["nonces_to_reveal"],
                    "publication_status": "published_with_nonces"
                }
                
        except Exception as e:
            raise Exception(f"Failed to publish ballot {ballot_id}: {str(e)}")
    
    def get_published_ballot(self, ballot_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a published ballot by ID.
        
        Args:
            ballot_id: The ballot identifier
            
        Returns:
            Published ballot data or None if not found
        """
        if ballot_id in self.cast_ballots:
            ballot_data = self.cast_ballots[ballot_id].copy()
            ballot_data["nonces_available"] = False
            return ballot_data
            
        elif ballot_id in self.audited_ballots:
            ballot_data = self.audited_ballots[ballot_id].copy()
            ballot_data["nonces_available"] = True
            ballot_data["ballot_nonces"] = self.ballot_nonces.get(ballot_id)
            return ballot_data
        
        return None
    
    def get_ballot_nonces(self, ballot_id: str) -> Optional[Dict[str, str]]:
        """
        Get nonces for a ballot (only available for audited ballots).
        
        Args:
            ballot_id: The ballot identifier
            
        Returns:
            Dictionary of nonces or None if not available
        """
        if ballot_id in self.audited_ballots:
            return self.ballot_nonces.get(ballot_id)
        return None
    
    def list_published_ballots(self, status_filter: Optional[str] = None) -> Dict[str, list]:
        """
        List all published ballots, optionally filtered by status.
        
        Args:
            status_filter: Optional filter ("CAST" or "AUDITED")
            
        Returns:
            Dictionary with cast_ballots and audited_ballots lists
        """
        result = {
            "cast_ballots": [],
            "audited_ballots": []
        }
        
        if not status_filter or status_filter.upper() == "CAST":
            result["cast_ballots"] = [
                {
                    "ballot_id": bid,
                    "ballot_hash": data["ballot_hash"],
                    "published_at": data["published_at"],
                    "nonces_available": False
                }
                for bid, data in self.cast_ballots.items()
            ]
        
        if not status_filter or status_filter.upper() == "AUDITED":
            result["audited_ballots"] = [
                {
                    "ballot_id": bid,
                    "ballot_hash": data["ballot_hash"],
                    "published_at": data["published_at"],
                    "nonces_available": True,
                    "nonce_count": len(self.ballot_nonces.get(bid, {}))
                }
                for bid, data in self.audited_ballots.items()
            ]
        
        return result
    
    def get_publication_stats(self) -> Dict[str, int]:
        """
        Get statistics about published ballots.
        
        Returns:
            Dictionary with ballot publication statistics
        """
        return {
            "total_ballots": len(self.cast_ballots) + len(self.audited_ballots),
            "cast_ballots": len(self.cast_ballots),
            "audited_ballots": len(self.audited_ballots),
            "nonces_stored": len(self.ballot_nonces)
        }
    
    def _get_timestamp(self) -> int:
        """Get current timestamp."""
        import time
        return int(time.time())


# Example Flask/API integration functions
def create_ballot_publication_endpoints(app, publisher: BallotPublisher):
    """
    Example function showing how to integrate with a Flask app.
    
    Args:
        app: Flask application instance
        publisher: BallotPublisher instance
    """
    
    @app.route('/api/ballots/publish', methods=['POST'])
    def publish_ballot_endpoint():
        """Endpoint to publish a ballot securely."""
        try:
            data = request.get_json()
            
            ballot_id = data.get('ballot_id')
            encrypted_ballot_response = data.get('encrypted_ballot_response')  
            ballot_status = data.get('ballot_status')
            
            if not all([ballot_id, encrypted_ballot_response, ballot_status]):
                return {"error": "Missing required fields"}, 400
            
            result = publisher.publish_ballot(
                ballot_id=ballot_id,
                encrypted_ballot_response=encrypted_ballot_response,
                ballot_status=ballot_status
            )
            
            return result, 200
            
        except Exception as e:
            return {"error": str(e)}, 500
    
    @app.route('/api/ballots/<ballot_id>', methods=['GET'])
    def get_ballot_endpoint(ballot_id):
        """Endpoint to retrieve a published ballot."""
        ballot = publisher.get_published_ballot(ballot_id)
        if ballot:
            return ballot, 200
        return {"error": "Ballot not found"}, 404
    
    @app.route('/api/ballots/<ballot_id>/nonces', methods=['GET'])
    def get_ballot_nonces_endpoint(ballot_id):
        """Endpoint to get nonces for an audited ballot."""
        nonces = publisher.get_ballot_nonces(ballot_id)
        if nonces:
            return {"ballot_id": ballot_id, "nonces": nonces}, 200
        return {"error": "Nonces not available for this ballot"}, 404
    
    @app.route('/api/ballots', methods=['GET'])
    def list_ballots_endpoint():
        """Endpoint to list all published ballots."""
        status_filter = request.args.get('status')
        ballots = publisher.list_published_ballots(status_filter)
        return ballots, 200
    
    @app.route('/api/ballots/stats', methods=['GET'])
    def get_stats_endpoint():
        """Endpoint to get publication statistics."""
        stats = publisher.get_publication_stats()
        return stats, 200


def example_usage():
    """
    Example usage of the BallotPublisher class.
    """
    print("=== BALLOT PUBLISHER EXAMPLE ===\n")
    
    # Initialize the publisher
    publisher = BallotPublisher()
    
    # Load sample ballot response
    try:
        with open("create_encrypted_ballot_response.json", "r") as f:
            sample_ballot_response = f.read()
    except FileNotFoundError:
        print("Sample ballot response file not found")
        return
    
    # Test publishing cast ballot
    print("1. Publishing CAST ballot...")
    cast_result = publisher.publish_ballot(
        ballot_id="ballot-001-cast",
        encrypted_ballot_response=sample_ballot_response,
        ballot_status="CAST"
    )
    print(f"Cast ballot published: {cast_result['publication_status']}")
    print(f"Nonces included: {'ballot_nonces' in cast_result}")
    
    # Test publishing audited ballot
    print("\n2. Publishing AUDITED ballot...")
    audited_result = publisher.publish_ballot(
        ballot_id="ballot-002-audited", 
        encrypted_ballot_response=sample_ballot_response,
        ballot_status="AUDITED"
    )
    print(f"Audited ballot published: {audited_result['publication_status']}")
    print(f"Nonces included: {'ballot_nonces' in audited_result}")
    print(f"Number of nonces: {len(audited_result.get('ballot_nonces', {}))}")
    
    # Test retrieval
    print("\n3. Retrieving published ballots...")
    cast_ballot = publisher.get_published_ballot("ballot-001-cast")
    audited_ballot = publisher.get_published_ballot("ballot-002-audited")
    
    print(f"Cast ballot nonces available: {cast_ballot['nonces_available']}")
    print(f"Audited ballot nonces available: {audited_ballot['nonces_available']}")
    
    # Test nonce retrieval
    print("\n4. Testing nonce retrieval...")
    cast_nonces = publisher.get_ballot_nonces("ballot-001-cast")
    audited_nonces = publisher.get_ballot_nonces("ballot-002-audited")
    
    print(f"Cast ballot nonces: {cast_nonces}")
    print(f"Audited ballot nonces count: {len(audited_nonces) if audited_nonces else 0}")
    
    # Test statistics
    print("\n5. Publication statistics:")
    stats = publisher.get_publication_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✓ Ballot publisher example completed successfully")


if __name__ == "__main__":
    example_usage()
