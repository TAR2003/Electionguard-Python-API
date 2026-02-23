# ElectionGuard Ballot Sanitization System

## Overview
This system provides secure ballot publication for ElectionGuard by separating nonces from encrypted ballots based on ballot status (CAST vs AUDITED).

## 🔐 Security Model

### Cast Ballots
- **Published**: Sanitized ballot with nonces set to `null`
- **Hidden**: All nonces kept secret for privacy
- **Purpose**: Maintain ballot privacy while allowing verification of encrypted values

### Audited Ballots  
- **Published**: Sanitized ballot + all extracted nonces
- **Revealed**: All nonces available for verification
- **Purpose**: Enable full audit verification of the encryption process

## 📁 Files Created

### 1. `ballot_sanitizer.py`
Core sanitization functions:
- `sanitize_ballot()` - Extracts nonces and returns sanitized ballot
- `prepare_ballot_for_publication()` - Handles CAST vs AUDITED logic
- `process_ballot_response()` - Processes complete ballot responses

### 2. `ballot_publisher.py` 
Integration class for API usage:
- `BallotPublisher` class for managing published ballots
- Separate storage for cast/audited ballots
- Nonce management with proper access controls

### 3. `test_ballot_sanitization.py`
Test script demonstrating the sanitization with your actual ballot data

### 4. `secure_api_example.py`
Example Flask API integration showing secure endpoints

## 🧪 Testing Results

Your actual encrypted ballot contained **5 nonces**:
- 1 top-level ballot nonce
- 1 contest-level nonce  
- 3 ballot selection nonces (including placeholder)

✅ **All 5 nonces successfully extracted**
✅ **Sanitized ballot has all nonces set to null**
✅ **Verification passed: No nonces remain in published cast ballots**

## 🔄 Usage Examples

### Basic Sanitization
```python
from ballot_sanitizer import sanitize_ballot

# Sanitize ballot and extract nonces
sanitized_ballot, extracted_nonces = sanitize_ballot(encrypted_ballot_json)

# sanitized_ballot: All nonces set to null
# extracted_nonces: Dictionary of all extracted nonces
```

### Publication Based on Status
```python
from ballot_sanitizer import prepare_ballot_for_publication

# For cast ballots - nonces hidden
cast_result = prepare_ballot_for_publication(ballot_json, "CAST")
# cast_result['nonces_to_reveal'] = None

# For audited ballots - nonces revealed
audited_result = prepare_ballot_for_publication(ballot_json, "AUDITED") 
# audited_result['nonces_to_reveal'] = {...} # All nonces
```

### API Integration
```python
from ballot_publisher import BallotPublisher

publisher = BallotPublisher()

# Publish cast ballot (secure - no nonces)
cast_result = publisher.publish_ballot("ballot-001", ballot_response, "CAST")

# Publish audited ballot (transparent - with nonces)
audit_result = publisher.publish_ballot("ballot-002", ballot_response, "AUDITED")
```

## 📊 Output Structure

### Cast Ballot Response
```json
{
  "ballot_id": "ballot-001-cast",
  "status": "CAST",
  "ballot_hash": "1A9DB671...",
  "encrypted_ballot": "{...sanitized ballot with nonce:null...}",
  "publication_status": "published_without_nonces"
}
```

### Audited Ballot Response  
```json
{
  "ballot_id": "ballot-002-audited",
  "status": "AUDITED", 
  "ballot_hash": "1A9DB671...",
  "encrypted_ballot": "{...sanitized ballot with nonce:null...}",
  "ballot_nonces": {
    "ballot_nonce": "2D875D435A964ED1...",
    "contest-1_nonce": "643CBB7C82E90D20...",
    "Alice Johnson": "A0560E0587D42866...",
    "Bob Smith": "08ACF97E34362BEF...",
    "contest-1-2-placeholder": "8FD51676195B95C4..."
  },
  "publication_status": "published_with_nonces"
}
```

## 🛡️ Security Features

1. **Complete Nonce Extraction**: Recursively finds and extracts ALL nonce fields
2. **Status-Based Access**: Nonces only revealed for audited ballots
3. **Immutable Separation**: Original ballot structure preserved, nonces cleanly separated
4. **Verification Built-in**: Automatic verification that no nonces remain in published ballots
5. **Placeholder Handling**: Properly handles placeholder selections

## 🚀 Integration Steps

1. **Import the modules**:
   ```python
   from ballot_sanitizer import prepare_ballot_for_publication
   from ballot_publisher import BallotPublisher
   ```

2. **Initialize publisher**:
   ```python
   publisher = BallotPublisher()
   ```

3. **Modify your ballot creation endpoint**:
   ```python
   # After creating encrypted ballot
   result = publisher.publish_ballot(ballot_id, encrypted_ballot_response, ballot_status)
   return result
   ```

4. **Add ballot retrieval endpoints**:
   - `/api/ballots/<id>` - Get published ballot
   - `/api/ballots/<id>/nonces` - Get nonces (audited only)
   - `/api/ballots` - List all ballots

## ✅ Verification

The system has been tested with your actual encrypted ballot data and successfully:
- ✅ Extracted all 5 nonces from the ballot structure
- ✅ Created sanitized versions with nonces set to null
- ✅ Maintained all other ballot data (ciphertext, proofs, hashes)
- ✅ Properly handled placeholder selections
- ✅ Verified no nonces remain in published cast ballots

## 🔧 Customization

The system is designed to be flexible:
- Extend `BallotPublisher` class for custom storage backends
- Modify nonce extraction logic for different ballot structures  
- Add custom validation or access controls
- Integrate with existing authentication systems

## 📝 Next Steps

1. Install Flask if using the API example: `pip install flask`
2. Integrate the `BallotPublisher` into your existing API
3. Update your ballot creation endpoints to use the sanitization
4. Add the secure ballot retrieval endpoints
5. Test with your specific ballot formats and requirements

The sanitization system is now ready for production use and will ensure proper security for both cast and audited ballots in your ElectionGuard implementation.
