import requests
import psycopg2
from psycopg2.extras import Json

# ---------- Global Variables ----------
JOINT_PUBLIC_KEY = "28681607485427281241152437303254855974467396950242211722612831578626527731198029699040562548433611283440907643679352559596117413928557236781979344621268159140404992390980639378899152231305341225628716156681506639673232663918479270796710673288670654509001710179980618219003537305626826481099895866290521714333752815496383535076582044263108452997202426424981533845834153127728725032208643634485985394197849009082271518216720128252921291801204935639610541627223512863535469722317792451516381974407622058204869398192305848060237363577374430227112855730961427208264096878265842780942807816269595757602147847043869221139862898685106846499128388046875227257783384479496367421227672047845731149449243782196003841324375405264498400530470885292752542877895256419014923295451593296422942861385321394178091090670123305503948254880618002292600542922447557718141399880145622376138621042372520440423479355336783238303814928139233710877598038325680479950053032849361456576339641649975503426796571896205390477527766765953775088479209777999417254319170694119015182894366133070323616059289457227278665341371465057013970332680901603392316115458769316445253106666298897618277039550861050533941817486584216065330030268725163320189088765129075455587544594"
COMMITMENT_HASH = "30578649540370000450388252453989321534268297241076730867753471018452882658073"
PARTY_NAMES = ["Pollman", "let me take a selfie", "All Rounder", "BIg dan of Seniors"]
CANDIDATE_NAMES = ["SMT - Souvik Mondol Turjo", "Iffat Bin Hoassain", "Ishrak Adit", "Hasnaen Adil"]

NUMBER_OF_GUARDIANS = 3
QUORUM = 2
TOTAL_NUMBER_OF_BALLOTS = 70
ELECTION_ID = 126   # Example

API_URL = "http://localhost:5000/create_encrypted_ballot"

# ---------- Database Connection ----------
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "amarvotelocaldb",
    "user": "postgres",
    "password": "123"
}

# ---------- Main Logic ----------
def insert_ballot(conn, election_id, status, cipher_text, hash_code, tracking_code):
    query = """
    INSERT INTO ballots (
        election_id, status, cipher_text, hash_code, tracking_code,
        master_nonce, proof, ballot_style, ballot_nonces, contest_hashes
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (tracking_code) DO NOTHING;
    """
    with conn.cursor() as cur:
        cur.execute(query, (
            election_id,
            status,
            cipher_text,
            hash_code,
            tracking_code,
            None,   # master_nonce
            None,   # proof
            None,   # ballot_style
            None, # ballot_nonces
            None  # contest_hashes
        ))
    conn.commit()

def main():
    conn = psycopg2.connect(**DB_CONFIG)

    for i in range(1, TOTAL_NUMBER_OF_BALLOTS + 1):
        ballot_id = f"ballot-{i}-extra"
        candidate_choice = CANDIDATE_NAMES[i % len(CANDIDATE_NAMES)]  # just cycling candidates

        payload = {
            "party_names": PARTY_NAMES,
            "candidate_names": CANDIDATE_NAMES,
            "candidate_name": candidate_choice,
            "ballot_id": ballot_id,
            "joint_public_key": JOINT_PUBLIC_KEY,
            "commitment_hash": COMMITMENT_HASH,
            "number_of_guardians": NUMBER_OF_GUARDIANS,
            "quorum": QUORUM
        }

        try:
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                insert_ballot(
                    conn,
                    election_id=ELECTION_ID,
                    status="cast",
                    cipher_text=data.get("encrypted_ballot"),
                    hash_code=data.get("ballot_hash"),
                    tracking_code=data.get("ballot_id")
                )
                print(f"✅ Inserted {ballot_id} into DB")
            else:
                print(f"⚠️ Failed for {ballot_id}: {data}")

        except Exception as e:
            print(f"❌ Error processing {ballot_id}: {e}")

    conn.close()

if __name__ == "__main__":
    main()
