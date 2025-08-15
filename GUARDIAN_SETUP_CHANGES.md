# Guardian Setup System Changes

## Overview

The guardian setup process has been modified to enhance security by ensuring that guardians' private keys and polynomials never leave their local environment.

## Previous System (setup_guardians)

```
Server Side:
1. Generate ALL guardian keys and polynomials
2. Return ALL private keys, public keys, and polynomials
3. Guardians receive their secrets from server

Risk: Sensitive cryptographic material generated and transmitted over network
```

## New System (setup_guardian)

```
Guardian Side:
1. Guardian generates private key locally
2. Guardian generates public key from private key
3. Guardian generates polynomial locally
4. Guardian keeps private key and polynomial SECRET
5. Guardian sends ONLY public key to server

Server Side:
1. Receives ONLY public key from guardian
2. Generates election structures using public key
3. Creates coefficient commitments and proofs
4. Returns election-related data (NO SECRETS)
```

## API Changes

### New Endpoint: `/setup_guardian`

**Request Format:**
```json
{
    "guardian_id": "guardian_1",
    "sequence_order": 1,
    "public_key": "12345678901234567890...",
    "number_of_guardians": 3,
    "quorum": 3,
    "party_names": ["Party A", "Party B"],
    "candidate_names": ["Alice", "Bob"]
}
```

**Response Format:**
```json
{
    "status": "success",
    "guardian_id": "guardian_1",
    "sequence_order": 1,
    "guardian_data": "{serialized guardian data}",
    "election_public_key": "{serialized public key}",
    "number_of_guardians": 3,
    "quorum": 3
}
```

### Existing Endpoint: `/setup_guardians` (Backward Compatibility)

This endpoint remains unchanged for existing implementations.

## Security Benefits

1. **Private Key Security**: Private keys never leave guardian's environment
2. **Polynomial Security**: Polynomial coefficients remain local
3. **Reduced Attack Surface**: Only public information transmitted
4. **Local Control**: Guardians have full control over their secrets
5. **Zero Trust**: Server never sees sensitive material

## Implementation Details

### Files Modified/Created:

1. **`api.py`**: Added new `/setup_guardian` endpoint
2. **`services/setup_guardian.py`**: New service for individual guardian setup
3. **`setup_guardian_api_format.txt`**: API format specification
4. **`test_setup_guardian.py`**: Test script demonstrating usage
5. **`README.md`**: Updated documentation

### Key Functions:

- **`setup_guardian_service()`**: Core logic for processing guardian public key
- **Guardian key generation**: Local functions for generating cryptographic material
- **Election structure creation**: Server-side generation of election-related data

## Usage Example

```python
from electionguard.group import g_pow_p, rand_q

# Guardian generates keys locally
private_key = rand_q()
public_key = g_pow_p(private_key)
polynomial = generate_polynomial(quorum)

# Guardian sends only public key to server
response = requests.post('/setup_guardian', json={
    'guardian_id': 'guardian_1',
    'sequence_order': 1,
    'public_key': str(int(public_key)),  # Only this is sent!
    'number_of_guardians': 3,
    'quorum': 3,
    'party_names': ['Party A', 'Party B'],
    'candidate_names': ['Alice', 'Bob']
})

# Guardian keeps private_key and polynomial locally
# Server returns election structures without any secrets
```

## Testing

Run the test script to validate the new functionality:

```bash
python test_setup_guardian.py
```

This will demonstrate:
1. Guardian key generation
2. API communication (public key only)
3. Server response processing
4. Local secret retention

## Migration Path

1. **Immediate**: New guardians can use `/setup_guardian`
2. **Gradual**: Existing systems continue using `/setup_guardians`
3. **Future**: Deprecate `/setup_guardians` when all systems migrated

## Compliance

This change aligns with cryptographic best practices:
- **Principle of Least Privilege**: Server only receives necessary information
- **Defense in Depth**: Multiple layers of secret protection
- **Zero Trust**: No assumption about server security
- **Local Control**: Guardians maintain control over sensitive material
