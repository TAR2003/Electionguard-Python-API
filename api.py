#!/usr/bin/env python

import sys
import io

# Windows: ensure stdout/stderr accept ALL Unicode (emoji, surrogates, etc.)
# without raising UnicodeEncodeError and corrupting request handling.
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import logging

# Suppress ElectionGuard's verbose INFO logging BEFORE importing any electionguard modules.
# Every crypto operation logs huge binary blobs (512-char hex keys, 512-byte binary data)
# via log_info(), and each call invokes inspect.stack() — together this adds 2-5s per endpoint.
# Setting WARNING level eliminates all INFO log processing, including inspect.stack() overhead.
logging.getLogger('electionguard').setLevel(logging.WARNING)

from flask import Flask, request, jsonify, g, Response
from typing import Dict, List, Optional, Tuple, Any
import gc
import random
from datetime import datetime
import uuid
import threading
import time
from collections import defaultdict
import hashlib
import json
import signal
import msgpack
from functools import wraps
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
import os
import base64
import secrets
import string
import logging
from functools import wraps
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()  # Add this at the top of your file
from electionguard.ballot import (
    BallotBoxState,
    CiphertextBallot,
    PlaintextBallot,
    PlaintextBallotSelection,
    PlaintextBallotContest,
    SubmittedBallot,
)
from electionguard.serialize import to_raw, from_raw
from binary_serialize import (
    to_binary_transport,
    from_binary_transport,
    from_binary_transport_to_dict,
    serialize_list_to_binary_list,
    deserialize_binary_list_to_list,
    deserialize_binary_list_to_dict_list
)
from electionguard.constants import get_constants
from electionguard.data_store import DataStore
from electionguard.decryption_mediator import DecryptionMediator
from electionguard.election import CiphertextElectionContext
from electionguard.election_polynomial import (
    LagrangeCoefficientsRecord,
    ElectionPolynomial
)
from electionguard.encrypt import EncryptionDevice, EncryptionMediator
from electionguard.guardian import Guardian
from electionguard.key_ceremony_mediator import KeyCeremonyMediator
from electionguard.key_ceremony import ElectionKeyPair, ElectionPublicKey
from electionguard.ballot_box import BallotBox, get_ballots
from electionguard.elgamal import ElGamalPublicKey, ElGamalSecretKey, ElGamalCiphertext
from electionguard.group import ElementModQ, ElementModP, g_pow_p, int_to_p, int_to_q
from electionguard.manifest import (
    Manifest,
    InternalManifest,
    GeopoliticalUnit,
    Party,
    Candidate,
    ContestDescription as Contest,
    SelectionDescription,
    BallotStyle,
    ElectionType,
    VoteVariationType,
    SpecVersion,
    ContactInformation,
    ReportingUnitType
)
from electionguard_tools.helpers.election_builder import ElectionBuilder
from electionguard.tally import (
    tally_ballots,
    CiphertextTally,
    PlaintextTally,
    CiphertextTallyContest,
    CiphertextTallySelection
)
from electionguard.type import BallotId, GuardianId
from electionguard.utils import get_optional
from electionguard.election_polynomial import ElectionPolynomial, Coefficient, SecretCoefficient, PublicCommitment
from electionguard.schnorr import SchnorrProof
from electionguard.elgamal import ElGamalKeyPair, ElGamalPublicKey, ElGamalSecretKey
from electionguard.hash import hash_elems
from electionguard.decryption_share import DecryptionShare, CompensatedDecryptionShare
from electionguard.decryption import (
    compute_decryption_share, 
    compute_decryption_share_for_ballot,
    compute_compensated_decryption_share,
    compute_compensated_decryption_share_for_ballot,
    decrypt_backup,
    compute_lagrange_coefficients_for_guardians as compute_lagrange_coeffs
)
from services.setup_guardians import setup_guardians_service
from services.guardian_key_ceremony import (
    init_guardian_ceremony_service,
    submit_guardian_keys_service,
    finalize_guardian_ceremony_service,
    get_ceremony_status_service
)
from services.create_encrypted_ballot import create_encrypted_ballot_service
from services.create_encrypted_tally import create_encrypted_tally_service
from services.create_partial_decryption import create_partial_decryption_service
from services.create_compensated_decryption_shares import create_compensated_decryption_service, compute_compensated_ballot_shares
from services.combine_decryption_shares import combine_decryption_shares_service
from services.create_partial_decryption_shares import compute_ballot_shares, compute_guardian_decryption_shares
from services.create_encrypted_ballot import create_election_manifest, create_plaintext_ballot
from services.create_encrypted_tally import ciphertext_tally_to_raw, raw_to_ciphertext_tally
from services.benaloh_challenge import benaloh_challenge_service

# Re-apply WARNING level after all ElectionGuard imports (ElectionGuardLog singleton now
# defaults to WARNING, but this ensures nothing else reset it during service imports).
logging.getLogger('electionguard').setLevel(logging.WARNING)

# Import ballot sanitization modules
from ballot_sanitizer import prepare_ballot_for_publication, process_ballot_response
from ballot_publisher import BallotPublisher

# Import post-quantum cryptography (Kyber1024)
try:
    import pqcrypto.kem.ml_kem_1024 as kyber1024
    from pqcrypto.kem.ml_kem_1024 import generate_keypair, encrypt, decrypt
    PQ_AVAILABLE = True
except ImportError:
    print("Warning: pqcrypto not available. Install with: pip install pqcrypto")
    PQ_AVAILABLE = False


#!/usr/bin/env python

# All your imports here...
from flask import Flask, request, jsonify, g
# ... rest of imports ...

# ===== ADD THIS SECTION HERE (before app = Flask(__name__)) =====
import multiprocessing
import os

# CRITICAL: Force spawn method to prevent fork-based deadlock in Docker
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass  # Already set

# Prevent semaphore issues
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
# ===== END ADDITION =====

app = Flask(__name__)
# ... rest of your code ...


# Flask Configuration for handling large files and long requests
# No MAX_CONTENT_LENGTH limit - allows unlimited request sizes
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development
app.config['JSON_SORT_KEYS'] = False  # Preserve JSON order for better performance
app.config['REQUEST_TIMEOUT'] = 300  # 5 minutes timeout per request
app.config['RESPONSE_TIMEOUT'] = 300  # 5 minutes response timeout

# Security Configuration
PQ_ALGORITHM = "ML-KEM-1024"  # Official NIST name
SCRYPT_SALT_LENGTH = 32
SCRYPT_LENGTH = 32
SCRYPT_N = 2**16  # Reduced from 2**20 for speed (still secure: ~65ms vs 3s)
SCRYPT_R = 8
SCRYPT_P = 1
AES_KEY_LENGTH = 32
PASSWORD_LENGTH = 32  # Reduced for speed (still 256-bit entropy)

# Master key - MUST be stored securely in production (HSM, Key Vault, etc.)
MASTER_KEY = os.environ.get('MASTER_KEY_PQ')
if not MASTER_KEY:
    print("WARNING: MASTER_KEY not set in environment. Using random key (data will be lost on restart)")
    MASTER_KEY = os.urandom(32)
elif isinstance(MASTER_KEY, str):
    print('master key found : ' , MASTER_KEY)
    MASTER_KEY = base64.b64decode(MASTER_KEY)

# Rate limiting storage (in production, use Redis/database)
rate_limit_storage = {}

# Initialize secure ballot publisher
ballot_publisher = BallotPublisher()

# Setup logging with thread info
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(threadName)s-%(thread)d] %(levelname)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Request tracking
request_tracking = {}
tracking_lock = threading.Lock()

def track_request(endpoint):
    """Decorator to track request execution and detect hangs"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            request_id = str(uuid.uuid4())[:8]
            thread_id = threading.current_thread().ident
            start_time = time.time()
            
            # Track this request
            with tracking_lock:
                request_tracking[request_id] = {
                    'endpoint': endpoint,
                    'thread_id': thread_id,
                    'start_time': start_time,
                    'status': 'started'
                }
            
            logger.info(f"[{request_id}] START {endpoint} (thread {thread_id})")
            
            try:
                result = f(*args, **kwargs)
                elapsed = time.time() - start_time
                
                with tracking_lock:
                    request_tracking[request_id]['status'] = 'completed'
                    request_tracking[request_id]['elapsed'] = elapsed
                
                logger.info(f"[{request_id}] COMPLETE {endpoint} in {elapsed:.2f}s")
                return result
                
            except Exception as e:
                elapsed = time.time() - start_time
                
                with tracking_lock:
                    request_tracking[request_id]['status'] = 'failed'
                    request_tracking[request_id]['error'] = str(e)
                    request_tracking[request_id]['elapsed'] = elapsed
                
                logger.error(f"[{request_id}] FAILED {endpoint} after {elapsed:.2f}s: {e}")
                raise
            
            finally:
                # Cleanup old tracking data (keep last 100)
                with tracking_lock:
                    if len(request_tracking) > 100:
                        old_keys = sorted(request_tracking.keys())[:50]
                        for k in old_keys:
                            del request_tracking[k]
        
        return wrapper
    return decorator

# def ## print_json(data, str_):
#     """Disabled file I/O to prevent blocking - use logger instead"""
#     try:
#         logger.info(f"Processing: {str_} with {len(data)} fields")
#     except:
#         pass  # Don't let logging failures affect processing

# def ## print_data(data, filename):
#     pass
#     # with open(filename, "w") as f:
#     #     json.dump(data, f, ensure_ascii=False, indent=4)


# Helper functions for binary serialization/deserialization (FAST - 10-50x faster than JSON)
def serialize_dict_to_string(data, label="dict"):
    """Convert dict to base64-encoded binary msgpack (FAST) with timing"""
    if isinstance(data, dict):
        start_time = time.time()
        result = to_binary_transport(data)
        elapsed = time.time() - start_time
        print(f"⏱️  SERIALIZE {label}: {elapsed*1000:.2f}ms (size: {len(result)} bytes)")
        return result
    return data

def deserialize_string_to_dict(data, label="dict"):
    """Convert base64-encoded binary msgpack to dict (FAST) with timing"""
    if isinstance(data, dict):
        # Already a dict (from request.json), return as-is
        return data
    elif isinstance(data, str):
        try:
            start_time = time.time()
            result = from_binary_transport_to_dict(data)
            elapsed = time.time() - start_time
            print(f"⏱️  DESERIALIZE {label}: {elapsed*1000:.2f}ms (size: {len(data)} bytes)")
            return result
        except Exception as e:
            raise ValueError(f"Invalid binary data: {e}")
    else:
        raise ValueError(f"Expected string or dict, got {type(data)}")

def serialize_list_of_dicts_to_list_of_strings(data, label="list"):
    """Convert List[dict] to List[base64 binary] (FAST) with timing"""
    if isinstance(data, list):
        if not data:
            return []
        if isinstance(data[0], dict):
            start_time = time.time()
            result = serialize_list_to_binary_list(data)
            elapsed = time.time() - start_time
            total_size = sum(len(item) for item in result)
            print(f"⏱️  SERIALIZE {label} ({len(data)} items): {elapsed*1000:.2f}ms (total: {total_size} bytes)")
            return result
    return data

def deserialize_list_of_strings_to_list_of_dicts(data, label="list"):
    """Convert List[base64 binary] to List[dict] (FAST) with timing"""
    if isinstance(data, list):
        if not data:
            return []
        if isinstance(data[0], dict):
            # Already a list of dicts (from request.json), return as-is
            return data
        elif isinstance(data[0], str):
            try:
                start_time = time.time()
                result = deserialize_binary_list_to_dict_list(data)
                elapsed = time.time() - start_time
                total_size = sum(len(item) for item in data)
                print(f"⏱️  DESERIALIZE {label} ({len(data)} items): {elapsed*1000:.2f}ms (from {total_size} bytes)")
                return result
            except Exception as e:
                raise ValueError(f"Invalid binary data in list: {e}")
        else:
            raise ValueError(f"Expected list of strings or dicts, got list of {type(data[0])}")
    elif isinstance(data, str):
        # Single string that should be parsed as JSON
        try:
            parsed = json.loads(data)
            if isinstance(parsed, list):
                return parsed
            else:
                return [parsed]
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")
    else:
        raise ValueError(f"Expected list or string, got {type(data)}")

def _bytes_to_str_deep(obj):
    """Recursively decode bytes → UTF-8 str for dicts/lists coming from msgpack raw=True mode."""
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    elif isinstance(obj, dict):
        return {_bytes_to_str_deep(k): _bytes_to_str_deep(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_bytes_to_str_deep(v) for v in obj]
    return obj


def get_request_data():
    """Parse request body: accepts both application/msgpack and application/json.

    Handles both the modern msgpack format (use_bin_type=True / raw=False) and
    the legacy format (use_bin_type=False / raw=True).  The legacy format stores
    byte strings as msgpack *raw* type, which cannot be decoded as UTF-8 when
    ``raw=False`` is used, causing a UnicodeDecodeError / UnpackValueError.  We
    silently fall back to raw=True and convert all byte values to strings.
    """
    ct = request.content_type or ''
    if 'msgpack' in ct:
        try:
            return msgpack.unpackb(request.data, raw=False)
        except (UnicodeDecodeError, ValueError):
            raw_data = msgpack.unpackb(request.data, raw=True)
            return _bytes_to_str_deep(raw_data)
    return request.json


def _sanitize_for_msgpack(obj):
    """Recursively replace lone surrogates so msgpack can UTF-8 encode all strings."""
    if isinstance(obj, dict):
        return {_sanitize_for_msgpack(k): _sanitize_for_msgpack(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_msgpack(v) for v in obj]
    elif isinstance(obj, str):
        try:
            obj.encode('utf-8')   # fast-path: already valid
            return obj
        except UnicodeEncodeError:
            # Replace lone surrogates with the Unicode replacement character
            return obj.encode('utf-8', errors='replace').decode('utf-8')
    return obj   # int, float, bool, bytes, None → pass through


def make_binary_response(data, status=200):
    """Return msgpack binary response (10-50x faster than JSON for large payloads).

    Note: msgpack raises ValueError (not UnicodeEncodeError) for strings with lone
    surrogates, so we preemptively sanitize if the first pack attempt fails.
    """
    try:
        packed = msgpack.packb(data, use_bin_type=True, default=str)
    except Exception as exc:
        # msgpack wraps UTF-8 errors as ValueError; sanitize lone surrogates and retry
        print(f"[make_binary_response] pack failed ({type(exc).__name__}: {exc}); sanitizing…")
        try:
            packed = msgpack.packb(_sanitize_for_msgpack(data), use_bin_type=True, default=str)
        except Exception as exc2:
            # Absolute last resort: return a plain ASCII error payload
            print(f"[make_binary_response] sanitized pack also failed: {exc2}")
            packed = msgpack.packb(
                {'status': 'error', 'message': f'Serialization error: {exc}'},
                use_bin_type=True
            )
            status = 500
    return Response(packed, status=status, mimetype='application/msgpack')


def safe_int_conversion(value):
    """Safely convert values to int, handling JSON string->int issues"""
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Cannot convert string '{value}' to integer")
    elif isinstance(value, float):
        return int(value)
    elif value is None:
        raise ValueError("Cannot convert None to integer")
    return value

# Global storage for election data
election_data = {
    'guardians': None,
    'joint_public_key': None,
    'commitment_hash': None,
    'manifest': None,
    'encrypted_ballots': [],
    'ciphertext_tally': None,
    'submitted_ballots': None,
    'guardian_shares': [],
    'number_of_guardians': 0,
    'quorum': 0
}

geopolitical_unit = GeopoliticalUnit(
    object_id="county-1",
    name="County 1",
    type=ReportingUnitType.county,
    contact_information=None,
)

ballot_style = BallotStyle(
    object_id="ballot-style-1",
    geopolitical_unit_ids=["county-1"],
    party_ids=None,
    image_uri=None,
)


def generate_ballot_hash(ballot: Any) -> str:
    """Generate a cryptographic hash for the ballot using ElectionGuard's built-in hash function."""
    if hasattr(ballot, 'crypto_hash'):
        # Use ElectionGuard's built-in crypto_hash method if available
        return ballot.crypto_hash.to_hex()
    else:
        # Fallback to serialization-based hashing for other objects
        ballot_bytes = to_raw(ballot).encode('utf-8')
        return hashlib.sha256(ballot_bytes).hexdigest()

def generate_ballot_hash_electionguard(ballot: Any) -> str:
    """Generate a cryptographic hash using ElectionGuard's hash_elems function."""
    if hasattr(ballot, 'object_id') and hasattr(ballot, 'crypto_hash'):
        # Use the ballot's built-in crypto_hash which is computed using ElectionGuard's hash_elems
        return ballot.crypto_hash.to_hex()
    else:
        # For other objects, serialize and hash using ElectionGuard's hash_elems
        serialized = to_raw(ballot)
        hash_result = hash_elems(serialized)
        return hash_result.to_hex()

def generate_ballot_hash_from_serialized(serialized_ballot: Dict) -> str:
    """Generate a SHA-256 hash from a serialized ballot dictionary."""
    import json
    # Convert dict to JSON string with consistent ordering
    ballot_json = json.dumps(serialized_ballot, sort_keys=True)
    return hashlib.sha256(ballot_json.encode('utf-8')).hexdigest()

# New helper functions for post-quantum cryptography
def rate_limit(max_requests=10, window_minutes=1):
    """Simple rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = datetime.now()
            
            # Clean old entries
            cutoff_time = current_time - timedelta(minutes=window_minutes)
            if client_ip in rate_limit_storage:
                rate_limit_storage[client_ip] = [
                    req_time for req_time in rate_limit_storage[client_ip] 
                    if req_time > cutoff_time
                ]
            
            # Check rate limit
            if client_ip not in rate_limit_storage:
                rate_limit_storage[client_ip] = []
            
            if len(rate_limit_storage[client_ip]) >= max_requests:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            rate_limit_storage[client_ip].append(current_time)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_input(data, required_fields):
    """Validate input data and check for required fields"""
    if not data:
        return "No data provided"
    
    for field in required_fields:
        if field not in data:
            return f"Missing required field: {field}"
    
    return None

def generate_strong_password():
    """Generate a 32-character cryptographically secure password (optimized for speed)"""
    # Optimized character set for speed while maintaining security
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(PASSWORD_LENGTH))

def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Optimized key derivation with caching for repeated operations"""
    kdf = Scrypt(
        salt=salt,
        length=SCRYPT_LENGTH,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        backend=default_backend()
    )
    return kdf.derive(password.encode('utf-8'))

def fast_encrypt_with_master_key(plaintext: bytes) -> bytes:
    """Optimized encryption with memory-efficient operations"""
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    cipher = Cipher(algorithms.AES(MASTER_KEY), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    
    # Process in one go for speed
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    
    # Minimize memory copies
    result = bytearray(12 + 16 + len(ciphertext))
    result[:12] = nonce
    result[12:28] = encryptor.tag
    result[28:] = ciphertext
    return bytes(result)

def fast_decrypt_with_master_key(ciphertext: bytes) -> bytes:
    """Optimized decryption with minimal memory allocations"""
    if len(ciphertext) < 28:
        raise ValueError("Invalid ciphertext length")
    
    # Direct slice access for speed
    nonce = ciphertext[:12]
    tag = ciphertext[12:28]
    actual_ciphertext = ciphertext[28:]
    
    cipher = Cipher(algorithms.AES(MASTER_KEY), modes.GCM(nonce, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(actual_ciphertext) + decryptor.finalize()

def generate_hmac(key: bytes, data: bytes) -> bytes:
    """Generate HMAC-SHA256 for data integrity verification (optimized)"""
    # Use SHA256 instead of SHA512 for speed (still secure)
    h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
    h.update(data)
    return h.finalize()

def verify_hmac(key: bytes, data: bytes, expected_hmac: bytes) -> bool:
    """Verify HMAC with constant-time comparison (optimized)"""
    try:
        actual_hmac = generate_hmac(key, data)
        return secrets.compare_digest(actual_hmac, expected_hmac)
    except Exception:
        return False

# Pre-compute HKDF info strings for speed
HKDF_INFO_HYBRID = b'ml-kem-1024-hybrid-enc-v1'
HKDF_INFO_HMAC = b'hmac-key-derivation-v1'

@app.route('/setup_guardians', methods=['POST'])
def api_setup_guardians():
    """API endpoint to setup guardians and create joint key."""
    try:
        endpoint_start = time.time()
        print('\n' + '='*80)
        print('🚀 SETUP_GUARDIANS API CALL STARTED')
        print('='*80)
        
        data = get_request_data()
        number_of_guardians = safe_int_conversion(data['number_of_guardians'])
        quorum = safe_int_conversion(data['quorum'])
        party_names = data['party_names']
        candidate_names = data['candidate_names']
        
        ## print_json(data, "setup_guardians")
        ## print_data(data, "./io/setup_guardians_data.json")

        # Call service function
        service_start = time.time()
        print(f"\n📊 COMPUTATION: Guardian setup & key ceremony...")
        result = setup_guardians_service(
            number_of_guardians,
            quorum,
            party_names,
            candidate_names
        )
        service_elapsed = time.time() - service_start
        print(f"✅ COMPUTATION COMPLETE: {service_elapsed*1000:.2f}ms")
        
        # Store election data
        election_data['guardians'] = result['guardians']
        election_data['joint_public_key'] = result['joint_public_key']
        election_data['commitment_hash'] = result['commitment_hash']
        election_data['manifest'] = create_election_manifest(party_names, candidate_names)
        election_data['number_of_guardians'] = result['number_of_guardians']
        election_data['quorum'] = result['quorum']
        
        # Build response with raw dicts/lists — msgpack handles binary transport natively
        print(f"\n📦 SERIALIZATION: Preparing response...")
        serialization_start = time.time()
        response = {
            'status': 'success',
            'joint_public_key': result['joint_public_key'],
            'commitment_hash': result['commitment_hash'],
            'guardian_data': result['guardian_data'],
            'private_keys': result['private_keys'],
            'public_keys': result['public_keys'],
            'polynomials': result['polynomials'],
            'number_of_guardians': result['number_of_guardians'],
            'quorum': result['quorum']
        }
        serialization_elapsed = time.time() - serialization_start
        print(f"✅ SERIALIZATION COMPLETE: {serialization_elapsed*1000:.2f}ms")
        
        ## print_json(response, "setup_guardians_response")
        ## print_data(response, "./io/setup_guardians_response.json")
        
        endpoint_elapsed = time.time() - endpoint_start
        print(f"\n{'='*80}")
        print(f"🎯 SETUP_GUARDIANS TOTAL TIME: {endpoint_elapsed*1000:.2f}ms")
        print(f"   ├─ Computation: {service_elapsed*1000:.2f}ms ({service_elapsed/endpoint_elapsed*100:.1f}%)")
        print(f"   └─ Serialization: {serialization_elapsed*1000:.2f}ms ({serialization_elapsed/endpoint_elapsed*100:.1f}%)")
        print('='*80 + '\n')
        
        return make_binary_response(response)
    
    except ValueError as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=500)

@app.route('/create_encrypted_ballot', methods=['POST'])
@track_request('/create_encrypted_ballot')
def api_create_encrypted_ballot():
    """API endpoint to create and encrypt a ballot with secure publication."""
    try:
        endpoint_start = time.time()
        logger.info('Creating encrypted ballot')
        data = get_request_data()
        party_names = data['party_names']
        candidate_names = data['candidate_names']
        candidate_name = data['candidate_name']
        ballot_id = data['ballot_id']
        joint_public_key = data['joint_public_key']  # Expecting string
        commitment_hash = data['commitment_hash']    # Expecting string
        
        # Get ballot status for secure publication (default to CAST for security)
        ballot_status = data.get('ballot_status', 'CAST').upper()
        if ballot_status not in ['CAST', 'AUDITED']:
            ballot_status = 'CAST'  # Default to most secure option
        
        ## print_json(data, "create_encrypted_ballot")
        ## print_data(data, "./io/create_encrypted_ballot_request.json")

        # Get election data with safe int conversion
        number_of_guardians = safe_int_conversion(data.get('number_of_guardians', 1))
        quorum = safe_int_conversion(data.get('quorum', 1))
        
        # Call service function to create the encrypted ballot
        service_start = time.time()
        result = create_encrypted_ballot_service(
            party_names,
            candidate_names,
            candidate_name,
            ballot_id,
            joint_public_key,
            commitment_hash,
            number_of_guardians,
            quorum,
            create_plaintext_ballot,
            create_election_manifest,
            generate_ballot_hash_electionguard
        )
        service_elapsed = time.time() - service_start
        
        # Don't store ballots in memory - keep API stateless
        # If you need to store ballots, do it in the backend database
        # election_data is only for temporary session data if needed
        
        # Create the complete ballot response for sanitization
        serialization_start = time.time()

        # Keep binary transport as the with-nonce version for casting/tallying.
        # (base64-encoded msgpack of the full CiphertextBallot, including nonces)
        encrypted_ballot_with_nonce = result['encrypted_ballot']

        # Decode binary transport -> dict -> JSON string so the ballot_publisher
        # sanitizer can parse it.  json.dumps on a base64 string would fail.
        ballot_dict_for_sanitization = from_binary_transport_to_dict(encrypted_ballot_with_nonce)
        ballot_json_for_sanitization = json.dumps(ballot_dict_for_sanitization)

        complete_ballot_response = {
            'status': 'success',
            'encrypted_ballot': ballot_json_for_sanitization,
            'ballot_hash': result['ballot_hash']
        }
        
        # Apply secure ballot publication based on ballot status
        try:
            publication_result = ballot_publisher.publish_ballot(
                ballot_id=ballot_id,
                encrypted_ballot_response=json.dumps(complete_ballot_response),
                ballot_status=ballot_status
            )
            
            # Create the final response based on ballot status
            response = {
                'status': 'success',
                'ballot_id': ballot_id,
                'ballot_status': ballot_status,
                'ballot_hash': publication_result['ballot_hash'],
                'encrypted_ballot': publication_result['encrypted_ballot'],
                'encrypted_ballot_with_nonce': encrypted_ballot_with_nonce,
                'publication_status': publication_result['publication_status']
            }
            
            # Add nonces only for audited ballots
            if ballot_status == 'AUDITED' and 'ballot_nonces' in publication_result:
                response['ballot_nonces'] = publication_result['ballot_nonces']
                response['nonces_available'] = True
            else:
                response['nonces_available'] = False
                
        except Exception as sanitization_error:
            print(f"Sanitization error: {sanitization_error}")
            # Fallback to unsanitized response if sanitization fails
            response = {
                'status': 'success',
                'encrypted_ballot': result['encrypted_ballot'],
                'ballot_hash': result['ballot_hash'],
                'encrypted_ballot_with_nonce': result['encrypted_ballot'],
                'warning': 'Ballot published without sanitization due to error',
                'sanitization_error': str(sanitization_error)
            }
        
        # Save the response to file for debugging
        # with open("create_encrypted_ballot_response.json", "w", encoding="utf-8") as f:
        #     json.dump(response, f, ensure_ascii=False, indent=2)

        # ## print_json(response, "create_encrypted_ballot_response")  # Disabled - causes blocking
        # ## print_data(response, "./io/create_encrypted_ballot_response.json")  # Disabled
        logger.info(f'Finished encrypting ballot - Status: {ballot_status}')
        
        serialization_elapsed = time.time() - serialization_start
        endpoint_elapsed = time.time() - endpoint_start
        
        # AGGRESSIVE memory cleanup to prevent accumulation across chunks
        import sys
        
        # Clear Python's internal type cache
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()
        
        # Force full garbage collection (generation 2 includes all objects)
        gc.collect(generation=2)
        
        # Note: We keep timing output minimal for ballot encryption since it's called frequently
        # Detailed timing is shown only for batch operations (tally, partial decryption, etc.)
        
        return make_binary_response(response)
    
    except ValueError as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=500)

@app.route('/benaloh_challenge', methods=['POST'])
@track_request('/benaloh_challenge')
def api_benaloh_challenge():
    """API endpoint to perform Benaloh challenge verification."""
    try:
        print('Benaloh challenge call at the microservice')
        # Accept both application/json and application/msgpack (Java backend sends msgpack)
        data = get_request_data()

        # Validate required fields
        required_fields = [
            'encrypted_ballot_with_nonce', 'party_names', 'candidate_names',
            'candidate_name', 'joint_public_key', 'commitment_hash',
            'number_of_guardians', 'quorum'
        ]

        validation_error = validate_input(data, required_fields)
        if validation_error:
            return make_binary_response({'status': 'error', 'message': validation_error}, status=400)

        encrypted_ballot_with_nonce = data['encrypted_ballot_with_nonce']
        party_names = data['party_names']
        candidate_names = data['candidate_names']
        candidate_name = data['candidate_name']
        joint_public_key = data['joint_public_key']
        commitment_hash = data['commitment_hash']
        number_of_guardians = safe_int_conversion(data['number_of_guardians'])
        quorum = safe_int_conversion(data['quorum'])

        ## print_json(data, "benaloh_challenge_request")

        # Call the Benaloh challenge service
        result = benaloh_challenge_service(
            encrypted_ballot_with_nonce=encrypted_ballot_with_nonce,
            party_names=party_names,
            candidate_names=candidate_names,
            candidate_name=candidate_name,
            joint_public_key=joint_public_key,
            commitment_hash=commitment_hash,
            number_of_guardians=number_of_guardians,
            quorum=quorum
        )

        ## print_json(result, "benaloh_challenge_response")
        print('Finished Benaloh challenge call at the microservice')

        if result['success']:
            return make_binary_response({
                'status': 'success',
                'match': result['match'],
                'message': result['message'],
                'ballot_id': result.get('ballot_id'),
                'verified_candidate': result.get('verified_candidate'),
                'expected_candidate': result.get('expected_candidate')
            })
        else:
            return make_binary_response({
                'status': 'error',
                'message': result['error']
            }, status=400)

    except ValueError as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=500)

@app.route('/health', methods=['GET'])
def api_health_check():
    """API endpoint for health check."""
    stats = ballot_publisher.get_publication_stats()
    
    # Check for stuck requests
    stuck_requests = []
    current_time = time.time()
    with tracking_lock:
        for req_id, req_info in request_tracking.items():
            if req_info['status'] == 'started':
                elapsed = current_time - req_info['start_time']
                if elapsed > 60:  # More than 1 minute
                    stuck_requests.append({
                        'request_id': req_id,
                        'endpoint': req_info['endpoint'],
                        'elapsed_seconds': int(elapsed),
                        'thread_id': req_info['thread_id']
                    })
    
    return jsonify({
        'status': 'healthy', 
        'ballot_publication_stats': stats,
        'active_requests': len([r for r in request_tracking.values() if r['status'] == 'started']),
        'stuck_requests': stuck_requests,
        'thread_count': threading.active_count()
    }), 200

@app.route('/ballots/<ballot_id>', methods=['GET'])
def api_get_published_ballot(ballot_id):
    """API endpoint to retrieve a published ballot (sanitized based on status)."""
    try:
        ballot = ballot_publisher.get_published_ballot(ballot_id)
        if ballot:
            return jsonify(ballot), 200
        return jsonify({"error": "Ballot not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ballots/<ballot_id>/nonces', methods=['GET'])
def api_get_ballot_nonces(ballot_id):
    """API endpoint to get nonces for a ballot (only available for audited ballots)."""
    try:
        nonces = ballot_publisher.get_ballot_nonces(ballot_id)
        if nonces:
            return jsonify({
                "ballot_id": ballot_id, 
                "nonces": nonces,
                "status": "AUDITED",
                "nonce_count": len(nonces)
            }), 200
        
        # Check if ballot exists but is cast (no nonces available)
        ballot = ballot_publisher.get_published_ballot(ballot_id)
        if ballot and not ballot.get('nonces_available', False):
            return jsonify({
                "error": "Nonces not available for cast ballots", 
                "ballot_status": "CAST",
                "message": "Nonces are only available for audited ballots"
            }), 403
        
        return jsonify({"error": "Ballot not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ballots', methods=['GET'])
def api_list_published_ballots():
    """API endpoint to list all published ballots with their publication status."""
    try:
        status_filter = request.args.get('status')  # Optional: 'CAST' or 'AUDITED'
        ballots = ballot_publisher.list_published_ballots(status_filter)
        
        # Add summary statistics
        stats = ballot_publisher.get_publication_stats()
        
        return jsonify({
            "ballots": ballots,
            "statistics": stats,
            "filter_applied": status_filter
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/publish_ballot', methods=['POST'])
def api_publish_existing_ballot():
    """API endpoint to publish an already created encrypted ballot with specific status."""
    try:
        data = request.json
        
        ballot_id = data.get('ballot_id')
        encrypted_ballot_response = data.get('encrypted_ballot_response')  
        ballot_status = data.get('ballot_status', 'CAST').upper()
        
        if not all([ballot_id, encrypted_ballot_response]):
            return jsonify({
                "error": "Missing required fields", 
                "required": ["ballot_id", "encrypted_ballot_response"],
                "optional": ["ballot_status"]
            }), 400
        
        if ballot_status not in ['CAST', 'AUDITED']:
            ballot_status = 'CAST'  # Default to most secure
        
        result = ballot_publisher.publish_ballot(
            ballot_id=ballot_id,
            encrypted_ballot_response=encrypted_ballot_response,
            ballot_status=ballot_status
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/create_encrypted_tally', methods=['POST'])
@track_request('/create_encrypted_tally')
def api_create_encrypted_tally():
    """API endpoint to tally encrypted ballots."""
    try:
        endpoint_start = time.time()
        print('\n' + '='*80)
        print('🚀 CREATE_ENCRYPTED_TALLY API CALL STARTED')
        print('='*80)
        
        logger.info('Creating encrypted tally')
        data = get_request_data()
        party_names = data['party_names']
        candidate_names = data['candidate_names']
        joint_public_key = data['joint_public_key']  # Expecting string
        commitment_hash = data['commitment_hash']    # Expecting string
        encrypted_ballots = data['encrypted_ballots'] # List of encrypted ballot strings
        
        print(f"\n📊 RECEIVED: {len(encrypted_ballots)} encrypted ballots")
        
        ## print_json(data, "create_encrypted_tally")
        # Dump the request to a file named "create_encrypted_tally_request.json"
        ## print_data(data, "./io/create_encrypted_tally_request.json")

        # Get election data with safe int conversion
        number_of_guardians = safe_int_conversion(data.get('number_of_guardians', 1))
        quorum = safe_int_conversion(data.get('quorum', 1))
        
        # Call service function
        service_start = time.time()
        print(f"\n📊 COMPUTATION: Tallying ballots...")
        result = create_encrypted_tally_service(
            party_names,
            candidate_names,
            joint_public_key,
            commitment_hash,
            encrypted_ballots,
            number_of_guardians,
            quorum,
            create_election_manifest,
            ciphertext_tally_to_raw
        )
        service_elapsed = time.time() - service_start
        print(f"✅ COMPUTATION COMPLETE: {service_elapsed*1000:.2f}ms")
        
        # Don't store tally data in memory - keep API stateless
        # Backend should handle persistent storage
        # election_data['ciphertext_tally'] = result['ciphertext_tally']
        # election_data['submitted_ballots'] = result['submitted_ballots']
        
        print(f"\n📦 SERIALIZATION: Preparing response...")
        serialization_start = time.time()
        response = {
            'status': 'success',
            'ciphertext_tally': result['ciphertext_tally'],
            'submitted_ballots': result['submitted_ballots']
        }
        serialization_elapsed = time.time() - serialization_start
        print(f"✅ SERIALIZATION COMPLETE: {serialization_elapsed*1000:.2f}ms")
        
        # ## print_data(response, "./io/create_encrypted_tally_response.json")  # Disabled
        # ## print_json(response, "create_encrypted_tally_response")  # Disabled
        logger.info('Finished creating encrypted tally')
        
        # Force garbage collection to free memory
        gc.collect()
        
        endpoint_elapsed = time.time() - endpoint_start
        print(f"\n{'='*80}")
        print(f"🎯 CREATE_ENCRYPTED_TALLY TOTAL TIME: {endpoint_elapsed*1000:.2f}ms")
        print(f"   ├─ Computation: {service_elapsed*1000:.2f}ms ({service_elapsed/endpoint_elapsed*100:.1f}%)")
        print(f"   └─ Serialization: {serialization_elapsed*1000:.2f}ms ({serialization_elapsed/endpoint_elapsed*100:.1f}%)")
        print('='*80 + '\n')
        
        return make_binary_response(response)
    
    except ValueError as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=500)

@app.route('/create_partial_decryption', methods=['POST'])
@track_request('/create_partial_decryption')
def api_create_partial_decryption():
    """API endpoint to compute decryption shares for a single guardian."""
    try:
        endpoint_start = time.time()
        print('\n' + '='*80)
        print('🚀 CREATE_PARTIAL_DECRYPTION API CALL STARTED')
        print('='*80)
        
        logger.info('Creating partial decryption')
        data = get_request_data()
        guardian_id = data['guardian_id']
        ## print_json(data, "create_partial_decryption")
        # Print the request body as JSON to a file named "partial_decryption_request.json"

        ## print_data(data, "./io/partial_decryption_request.json")

        # Deserialize single guardian data from string (if available)
        print(f"\n📦 DESERIALIZATION: Processing guardian {guardian_id} data...")
        deserialize_start = time.time()
        
        guardian_data = None
        if data.get('guardian_data'):
            try:
                guardian_data = deserialize_string_to_dict(data['guardian_data'], label="guardian_data")
            except Exception as e:
                raise ValueError(f"Error deserializing guardian_data: {e}")
            
        try:
            private_key = deserialize_string_to_dict(data['private_key'], label="private_key")
        except Exception as e:
            raise ValueError(f"Error deserializing private_key: {e}")
            
        try:
            public_key = deserialize_string_to_dict(data['public_key'], label="public_key")
        except Exception as e:
            raise ValueError(f"Error deserializing public_key: {e}")
            
        # Polynomial is no longer required from the request
        # We'll create a minimal polynomial internally if needed
        party_names = data['party_names']
        candidate_names = data['candidate_names']
        
        # Deserialize dict from string with error context
        try:
            ciphertext_tally_json = deserialize_string_to_dict(data['ciphertext_tally'], label="ciphertext_tally")
        except Exception as e:
            raise ValueError(f"Error deserializing ciphertext_tally: {e}")
            
        # Deserialize submitted_ballots from list of strings to list of dicts
        try:
            submitted_ballots_json = deserialize_list_of_strings_to_list_of_dicts(data['submitted_ballots'], label="submitted_ballots")
        except Exception as e:
            raise ValueError(f"Error deserializing submitted_ballots: {e}")
        
        deserialize_elapsed = time.time() - deserialize_start
        print(f"✅ DESERIALIZATION COMPLETE: {deserialize_elapsed*1000:.2f}ms")
            
        joint_public_key = data['joint_public_key']
        commitment_hash = data['commitment_hash']
        
        # Get election data with safe int conversion
        number_of_guardians = safe_int_conversion(data.get('number_of_guardians', 1))
        quorum = safe_int_conversion(data.get('quorum', 1))
        
        # Call service function with single guardian data
        service_start = time.time()
        print(f"\n📊 COMPUTATION: Computing decryption shares...")
        result = create_partial_decryption_service(
            party_names,
            candidate_names,
            guardian_id,
            guardian_data,
            private_key,
            public_key,
            None,  # polynomial no longer required
            ciphertext_tally_json,
            submitted_ballots_json,
            joint_public_key,
            commitment_hash,
            number_of_guardians,
            quorum,
            create_election_manifest,
            raw_to_ciphertext_tally,
            compute_ballot_shares
        )
        service_elapsed = time.time() - service_start
        print(f"✅ COMPUTATION COMPLETE: {service_elapsed*1000:.2f}ms")
        
        print(f"\n📦 SERIALIZATION: Preparing response...")
        serialization_start = time.time()
        response = {
            'status': 'success',
            'guardian_public_key': result['guardian_public_key'],
            'tally_share': result['tally_share'],
            'ballot_shares': result['ballot_shares']
        }
        serialization_elapsed = time.time() - serialization_start
        print(f"✅ SERIALIZATION COMPLETE: {serialization_elapsed*1000:.2f}ms")
        
        # ## print_data(response, "./io/create_partial_decryption_response.json")  # Disabled
        # ## print_json(response, "create_partial_decryption_response")  # Disabled
        logger.info('Finished creating partial decryption')
        
        # Force garbage collection to free memory
        gc.collect()
        
        endpoint_elapsed = time.time() - endpoint_start
        print(f"\n{'='*80}")
        print(f"🎯 CREATE_PARTIAL_DECRYPTION TOTAL TIME: {endpoint_elapsed*1000:.2f}ms")
        print(f"   ├─ Deserialization: {deserialize_elapsed*1000:.2f}ms ({deserialize_elapsed/endpoint_elapsed*100:.1f}%)")
        print(f"   ├─ Computation: {service_elapsed*1000:.2f}ms ({service_elapsed/endpoint_elapsed*100:.1f}%)")
        print(f"   └─ Serialization: {serialization_elapsed*1000:.2f}ms ({serialization_elapsed/endpoint_elapsed*100:.1f}%)")
        print('='*80 + '\n')
        
        return make_binary_response(response)
    
    except ValueError as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=500)

@app.route('/create_compensated_decryption', methods=['POST'])
@track_request('/create_compensated_decryption')
def api_create_compensated_decryption():
    """API endpoint to compute compensated decryption shares for missing guardians."""
    try:
        endpoint_start = time.time()
        
        # Extract data from request
        logger.info('Creating compensated decryption')
        data = get_request_data()
        available_guardian_id = data['available_guardian_id']
        missing_guardian_id = data['missing_guardian_id']
        ## print_json(data, "create_compensated_decryption")
        # Dump the request to a file named "create_compensated_decryption_request.json"
        ## print_data(data, "./io/create_compensated_decryption_request.json")

        # Deserialize single guardian data from strings
        deserialize_start = time.time()
        try:
            available_guardian_data = deserialize_string_to_dict(data['available_guardian_data'])
        except Exception as e:
            raise ValueError(f"Error deserializing available_guardian_data: {e}")
            
        try:
            missing_guardian_data = deserialize_string_to_dict(data['missing_guardian_data'])
        except Exception as e:
            raise ValueError(f"Error deserializing missing_guardian_data: {e}")
            
        try:
            available_private_key = deserialize_string_to_dict(data['available_private_key'])
        except Exception as e:
            raise ValueError(f"Error deserializing available_private_key: {e}")
            
        try:
            available_public_key = deserialize_string_to_dict(data['available_public_key'])
        except Exception as e:
            raise ValueError(f"Error deserializing available_public_key: {e}")
            
        try:
            available_polynomial = deserialize_string_to_dict(data['available_polynomial'])
        except Exception as e:
            raise ValueError(f"Error deserializing available_polynomial: {e}")
            
        party_names = data['party_names']
        candidate_names = data['candidate_names']
        
        # Deserialize dict from string with error context
        try:
            ciphertext_tally_json = deserialize_string_to_dict(data['ciphertext_tally'])
        except Exception as e:
            raise ValueError(f"Error deserializing ciphertext_tally: {e}")
            
        # Deserialize submitted_ballots from list of strings to list of dicts
        try:
            submitted_ballots_json = deserialize_list_of_strings_to_list_of_dicts(data['submitted_ballots'])
        except Exception as e:
            raise ValueError(f"Error deserializing submitted_ballots: {e}")
        joint_public_key = data['joint_public_key']
        commitment_hash = data['commitment_hash']
        
        # Get election data with safe int conversion
        number_of_guardians = safe_int_conversion(data.get('number_of_guardians', 1))
        quorum = safe_int_conversion(data.get('quorum', 1))
        
        deserialize_elapsed = time.time() - deserialize_start
        
        # Call service function
        service_start = time.time()
        result = create_compensated_decryption_service(
            party_names,
            candidate_names,
            available_guardian_id,
            missing_guardian_id,
            available_guardian_data,
            missing_guardian_data,
            available_private_key,
            available_public_key,
            available_polynomial,
            ciphertext_tally_json,
            submitted_ballots_json,
            joint_public_key,
            commitment_hash,
            number_of_guardians,
            quorum,
            create_election_manifest,
            raw_to_ciphertext_tally,
            compute_compensated_ballot_shares
        )
        service_elapsed = time.time() - service_start

        # Format response
        serialization_start = time.time()
        response = {
            'status': 'success',
            'compensated_tally_share': result['compensated_tally_share'],
            'compensated_ballot_shares': result['compensated_ballot_shares']
        }
        serialization_elapsed = time.time() - serialization_start
        
        # ## print_data(response, "./io/create_compensated_decryption_response.json")  # Disabled
        logger.info('Finished creating compensated decryption')
        
        # Force garbage collection to free memory
        gc.collect()
        
        endpoint_elapsed = time.time() - endpoint_start
        # Note: Timing output kept minimal for compensated decryption (called frequently in loops)
        
        return make_binary_response(response)
    
    except ValueError as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=400)
        


@app.route('/combine_decryption_shares', methods=['POST'])
@track_request('/combine_decryption_shares')
def api_combine_decryption_shares():
    """API endpoint to combine decryption shares with quorum support."""
    try:
        endpoint_start = time.time()
        print('\n' + '='*80)
        print('🚀 COMBINE_DECRYPTION_SHARES API CALL STARTED')
        print('='*80)
        
        # Extract data from request
        data = get_request_data()
        party_names = data['party_names']
        candidate_names = data['candidate_names']
        joint_public_key = data['joint_public_key']
        commitment_hash = data['commitment_hash']
        ## print_json(data, "combine_decryption_shares")
        ## print_data(data, "./io/combine_decryption_shares_request.json")
        
        # Deserialize dict from string with error context
        print(f"\n📦 DESERIALIZATION: Processing input data...")
        deserialize_start = time.time()
        
        try:
            ciphertext_tally_json = deserialize_string_to_dict(data['ciphertext_tally'], label="ciphertext_tally")
        except Exception as e:
            raise ValueError(f"Error deserializing ciphertext_tally: {e}")
        
        # Deserialize list of strings to list of dicts for submitted_ballots
        try:
            submitted_ballots_json = deserialize_list_of_strings_to_list_of_dicts(data['submitted_ballots'], label="submitted_ballots")
        except Exception as e:
            raise ValueError(f"Error deserializing submitted_ballots: {e}")
        
        # Deserialize guardian_data from list of strings to list of dicts
        try:
            guardian_data = deserialize_list_of_strings_to_list_of_dicts(data['guardian_data'], label="guardian_data")
        except Exception as e:
            raise ValueError(f"Error deserializing guardian_data: {e}")

        # Reconstruct available_guardian_shares from separate arrays
        available_guardian_shares = {}
        available_guardian_ids_list = data.get('available_guardian_ids', [])
        available_guardian_public_keys = data.get('available_guardian_public_keys', [])
        available_tally_shares = data.get('available_tally_shares', [])
        available_ballot_shares = data.get('available_ballot_shares', [])
        
        for i, guardian_id in enumerate(available_guardian_ids_list):
            try:
                available_guardian_shares[guardian_id] = {
                    'guardian_public_key': available_guardian_public_keys[i],
                    'tally_share': available_tally_shares[i],
                    'ballot_shares': deserialize_string_to_dict(available_ballot_shares[i], label=f"ballot_shares_{guardian_id}") if isinstance(available_ballot_shares[i], str) else available_ballot_shares[i]
                }
            except Exception as e:
                raise ValueError(f"Error reconstructing available_guardian_shares for {guardian_id}: {e}")
        
        # Reconstruct compensated_shares from separate arrays
        all_compensated_shares = {}
        missing_guardian_ids_list = data.get('missing_guardian_ids', [])
        compensating_guardian_ids_list = data.get('compensating_guardian_ids', [])
        compensated_tally_shares = data.get('compensated_tally_shares', [])
        compensated_ballot_shares = data.get('compensated_ballot_shares', [])
        
        for i in range(len(missing_guardian_ids_list)):
            try:
                missing_guardian_id = missing_guardian_ids_list[i]
                compensating_guardian_id = compensating_guardian_ids_list[i]
                
                if missing_guardian_id not in all_compensated_shares:
                    all_compensated_shares[missing_guardian_id] = {}
                
                all_compensated_shares[missing_guardian_id][compensating_guardian_id] = {
                    'compensated_tally_share': compensated_tally_shares[i],
                    'compensated_ballot_shares': deserialize_string_to_dict(compensated_ballot_shares[i]) if isinstance(compensated_ballot_shares[i], str) else compensated_ballot_shares[i]
                }
            except Exception as e:
                raise ValueError(f"Error reconstructing compensated_shares: {e}")
        
        # Get the required quorum with safe int conversion
        quorum = safe_int_conversion(data.get('quorum', len(guardian_data)))
        number_of_guardians = safe_int_conversion(data.get('number_of_guardians', len(guardian_data)))
        
        deserialize_elapsed = time.time() - deserialize_start
        print(f"✅ DESERIALIZATION COMPLETE: {deserialize_elapsed*1000:.2f}ms")
        
        # Determine which guardians are available and which are missing
        available_guardian_ids = set(available_guardian_shares.keys())
        all_guardian_ids = {g['id'] for g in guardian_data}
        missing_guardian_ids = all_guardian_ids - available_guardian_ids
        
        print(f"\n👥 GUARDIAN STATUS:")
        print(f"   - Available guardians: {sorted(available_guardian_ids)}")
        print(f"   - Missing guardians: {sorted(missing_guardian_ids)}")
        print(f"   - All guardian IDs: {sorted(all_guardian_ids)}")
        print(f"   - Quorum required: {quorum}, Available: {len(available_guardian_ids)}")
        print(f"   - Submitted ballots: {len(submitted_ballots_json)}")
        
        # Validate we have enough guardians
        if len(available_guardian_ids) < quorum:
            raise ValueError(f"Insufficient guardians available. Need {quorum}, have {len(available_guardian_ids)}")
        
        # Filter compensated shares to ONLY include the missing guardians
        # This is where the backend determines which guardians need compensation
        filtered_compensated_shares = {}
        for missing_guardian_id in missing_guardian_ids:
            if missing_guardian_id in all_compensated_shares:
                filtered_compensated_shares[missing_guardian_id] = all_compensated_shares[missing_guardian_id]
                print(f"Including compensated shares for missing guardian: {missing_guardian_id}")
            else:
                raise ValueError(f"Missing compensated shares for guardian {missing_guardian_id}")
        
        # Log what we're filtering out
        excluded_guardians = set(all_compensated_shares.keys()) - missing_guardian_ids
        if excluded_guardians:
            print(f"Excluding compensated shares for available guardians: {sorted(excluded_guardians)}")
        
        # Call service function
        print(f"\n📊 COMPUTATION: Combining decryption shares...")
        service_start = time.time()
        results = combine_decryption_shares_service(
            party_names,
            candidate_names,
            joint_public_key,
            commitment_hash,
            ciphertext_tally_json,
            submitted_ballots_json,
            guardian_data,
            available_guardian_shares,
            filtered_compensated_shares,
            quorum,
            create_election_manifest,
            raw_to_ciphertext_tally,
            generate_ballot_hash,
            generate_ballot_hash_electionguard
        )
        service_elapsed = time.time() - service_start
        print(f"✅ COMPUTATION COMPLETE: {service_elapsed*1000:.2f}ms")
        
        # Format response - ensure all nested dicts are serialized to strings
        print(f"\n📦 SERIALIZATION: Preparing response...")
        serialization_start = time.time()
        response = {
            'status': 'success',
            'results': results
        }
        serialization_elapsed = time.time() - serialization_start
        print(f"✅ SERIALIZATION COMPLETE: {serialization_elapsed*1000:.2f}ms")
        
        # ## print_json(response, "combine_decryption_shares_response")  # Disabled
        # ## print_data(response, "./io/combine_decryption_shares_response.json")  # Disabled
        logger.info('Finished combining decryption shares')
        
        # Force garbage collection to free memory
        gc.collect()
        
        endpoint_elapsed = time.time() - endpoint_start
        print(f"\n{'='*80}")
        print(f"🎯 COMBINE_DECRYPTION_SHARES TOTAL TIME: {endpoint_elapsed*1000:.2f}ms")
        print(f"   ├─ Deserialization: {deserialize_elapsed*1000:.2f}ms ({deserialize_elapsed/endpoint_elapsed*100:.1f}%)")
        print(f"   ├─ Computation: {service_elapsed*1000:.2f}ms ({service_elapsed/endpoint_elapsed*100:.1f}%)")
        print(f"   └─ Serialization: {serialization_elapsed*1000:.2f}ms ({serialization_elapsed/endpoint_elapsed*100:.1f}%)")
        print('='*80 + '\n')
        
        return make_binary_response(response)
    
    except ValueError as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return make_binary_response({'status': 'error', 'message': str(e)}, status=500)

@app.route('/api/encrypt', methods=['POST'])
# @rate_limit(max_requests=10, window_minutes=1)
def encrypt_it():
    """
    Encrypt endpoint with quantum-resistant encryption and HMAC protection (optimized)
    
    Returns:
    - encrypted_data: The encrypted private key (Storage 1)
    - credentials: Contains all metadata + HMAC tag (Storage 2)
    """
    if not PQ_AVAILABLE:
        logger.error("Post-quantum cryptography not available")
        return make_binary_response({'error': 'Post-quantum cryptography not available'}, 501)

    data = get_request_data()
    validation_error = validate_input(data, ['private_key'])
    if validation_error:
        logger.warning(f"Validation error: {validation_error}")
        return make_binary_response({'error': validation_error}, 400)

    try:
        # Input validation (optimized)
        private_key = data['private_key']
        if not isinstance(private_key, str) or len(private_key) > 100000:
            return jsonify({'error': 'Invalid private key format or size'}), 400

        # Generate optimized password and salt
        password = generate_strong_password()
        salt = os.urandom(SCRYPT_SALT_LENGTH)
        
        # Post-quantum operations (these are the fastest part)
        pq_public_key, pq_private_key = generate_keypair()
        pq_ciphertext, pq_shared_secret = encrypt(pq_public_key)
        
        # Optimized key derivation
        password_key = derive_key_from_password(password, salt)
        combined_key = HKDF(
            algorithm=hashes.SHA256(),
            length=AES_KEY_LENGTH,
            salt=salt,
            info=HKDF_INFO_HYBRID,
            backend=default_backend()
        ).derive(password_key + pq_shared_secret)

        # Fast encryption of private key
        nonce = os.urandom(12)
        cipher = Cipher(algorithms.AES(combined_key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        
        private_key_bytes = private_key.encode('utf-8')
        encrypted_data = encryptor.update(private_key_bytes) + encryptor.finalize()

        # Fast password encryption
        encrypted_password = fast_encrypt_with_master_key(password.encode('utf-8'))

        # Create credentials structure (without HMAC tag first)
        credentials_data = {
            'version': '1.0',
            'algorithm': PQ_ALGORITHM,
            'salt': base64.b64encode(salt).decode(),
            'pq_private_key': base64.b64encode(pq_private_key).decode(),
            'pq_ciphertext': base64.b64encode(pq_ciphertext).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'tag': base64.b64encode(encryptor.tag).decode(),
            'encrypted_password': base64.b64encode(encrypted_password).decode()
        }
        
        # Serialize credentials for HMAC calculation
        credentials_json = json.dumps(credentials_data, separators=(',', ':')).encode('utf-8')
        
        # Generate HMAC for credentials integrity
        hmac_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=HKDF_INFO_HMAC,
            backend=default_backend()
        ).derive(combined_key)
        
        hmac_tag = generate_hmac(hmac_key, credentials_json)
        
        # Add HMAC tag to credentials
        credentials_data['hmac_tag'] = base64.b64encode(hmac_tag).decode()
        
        # Final credentials with HMAC tag
        final_credentials = json.dumps(credentials_data, separators=(',', ':')).encode('utf-8')

        logger.info(f"Successful encryption for IP: {request.remote_addr}")
        
        # Return only 2 storage items instead of 3
        return make_binary_response({
            'status': 'success',
            'encrypted_data': base64.b64encode(encrypted_data).decode(),  # Storage 1
            'credentials': base64.b64encode(final_credentials).decode()    # Storage 2 (includes HMAC)
        })

    except Exception as e:
        logger.error(f"Encryption error: {str(e)}")
        return make_binary_response({'status': 'error', 'message': 'Internal server error'}, 500)

@app.route('/api/decrypt', methods=['POST'])
# @rate_limit(max_requests=10, window_minutes=1)
def decrypt_it():
    """
    Decrypt endpoint with HMAC verification and quantum-safe decryption (optimized)
    
    Expects:
    - encrypted_data: The encrypted private key (from Storage 1)
    - credentials: Contains all metadata + HMAC tag (from Storage 2)
    """
    if not PQ_AVAILABLE:
        logger.error("Post-quantum cryptography not available")
        return make_binary_response({'error': 'Post-quantum cryptography not available'}, 501)

    data = get_request_data()
    validation_error = validate_input(data, ['encrypted_data', 'credentials'])
    if validation_error:
        logger.warning(f"Validation error: {validation_error}")
        return make_binary_response({'error': validation_error}, 400)

    try:
        # Fast decode and parse credentials
        credentials_json = base64.b64decode(data['credentials'])
        credentials = json.loads(credentials_json.decode('utf-8'))
        
        # Version check
        if credentials.get('version') != '1.0':
            return make_binary_response({'error': 'Unsupported credential version'}, 400)
        
        # Extract HMAC tag from credentials
        if 'hmac_tag' not in credentials:
            return make_binary_response({'error': 'Missing HMAC tag in credentials'}, 400)
        
        hmac_tag = base64.b64decode(credentials['hmac_tag'])
        
        # Create credentials without HMAC tag for verification
        credentials_for_verification = {k: v for k, v in credentials.items() if k != 'hmac_tag'}
        credentials_for_verification_json = json.dumps(credentials_for_verification, separators=(',', ':')).encode('utf-8')
        
        # Fast parameter extraction
        salt = base64.b64decode(credentials['salt'])
        pq_private_key = base64.b64decode(credentials['pq_private_key'])
        pq_ciphertext = base64.b64decode(credentials['pq_ciphertext'])
        
        # Post-quantum decryption
        pq_shared_secret = decrypt(pq_private_key, pq_ciphertext)
        
        # Fast password decryption
        encrypted_password = base64.b64decode(credentials['encrypted_password'])
        password = fast_decrypt_with_master_key(encrypted_password).decode('utf-8')
        
        # Reconstruct combined key
        password_key = derive_key_from_password(password, salt)
        combined_key = HKDF(
            algorithm=hashes.SHA256(),
            length=AES_KEY_LENGTH,
            salt=salt,
            info=HKDF_INFO_HYBRID,
            backend=default_backend()
        ).derive(password_key + pq_shared_secret)
        
        # Verify HMAC integrity of credentials
        hmac_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=HKDF_INFO_HMAC,
            backend=default_backend()
        ).derive(combined_key)
        
        if not verify_hmac(hmac_key, credentials_for_verification_json, hmac_tag):
            logger.warning(f"HMAC verification failed for IP: {request.remote_addr}")
            return make_binary_response({'error': 'Authentication failed - credentials tampered'}, 403)

        # Fast decryption of private key
        nonce = base64.b64decode(credentials['nonce'])
        tag = base64.b64decode(credentials['tag'])
        encrypted_data = base64.b64decode(data['encrypted_data'])
        
        cipher = Cipher(algorithms.AES(combined_key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

        logger.info(f"Successful decryption for IP: {request.remote_addr}")
        
        return make_binary_response({
            'status': 'success',
            'private_key': decrypted_data.decode('utf-8')
        })

    except Exception as e:
        logger.error(f"Decryption error: {str(e)}")
        return make_binary_response({'status': 'error', 'message': 'Decryption failed'}, 400)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'pq_available': PQ_AVAILABLE,
        'algorithm': PQ_ALGORITHM if PQ_AVAILABLE else None,
        'storage_design': '2-storage (encrypted_data + credentials_with_hmac)'
    }), 200

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'Request too large'}), 413

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({'error': 'Rate limit exceeded'}), 429

if __name__ == '__main__':
    if not PQ_AVAILABLE:
        print("Warning: Running without post-quantum cryptography support")
    
    # Security headers
    @app.after_request
    def after_request(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    print("Starting development server with enhanced security and 2-storage design...")
    print("IMPORTANT: Use proper WSGI server and SSL certificates in production!")
    print("Storage Design: encrypted_data (Storage 1) + credentials_with_hmac (Storage 2)")
    print("Configuration: Unlimited payload size, High thread count, Stateless operation")
    print("Memory Manager: Aggressive GC, No state accumulation, Chunk-safe processing")

    # Fix Windows loopback latency: Nagle's algorithm + TCP delayed ACKs add ~2s per request.
    # StreamRequestHandler.disable_nagle_algorithm = True sets TCP_NODELAY on each connection.
    from werkzeug.serving import WSGIRequestHandler

    class NagleDisabledHandler(WSGIRequestHandler):
        """Disables Nagle's algorithm via the built-in disable_nagle_algorithm flag."""
        disable_nagle_algorithm = True  # Sets TCP_NODELAY in StreamRequestHandler.setup()

    NagleDisabledHandler.protocol_version = "HTTP/1.1"  # Keep-alive

    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=False, 
        threaded=True,
        processes=1,
        use_reloader=False,
        request_handler=NagleDisabledHandler
    )