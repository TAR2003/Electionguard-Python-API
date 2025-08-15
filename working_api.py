#!/usr/bin/env python3
"""
Minimal working API server with just the setup_guardian endpoint.
This version removes heavy dependencies that cause import errors.
"""

from flask import Flask, request, jsonify
import json
import sys
import os

app = Flask(__name__)

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def minimal_setup_guardian_service(guardian_id, sequence_order, public_key, number_of_guardians, quorum, party_names, candidate_names):
    """
    Minimal service that mimics the ElectionGuard setup_guardian behavior
    without heavy cryptographic dependencies.
    """

    # Validate inputs
    if quorum > number_of_guardians:
        raise ValueError('Quorum cannot be greater than number of guardians')

    if quorum < 1:
        raise ValueError('Quorum must be at least 1')

    if sequence_order < 1 or sequence_order > number_of_guardians:
        raise ValueError(
            'Sequence order must be between 1 and number_of_guardians')

    # Create guardian data structure (simplified)
    guardian_data = {
        'id': guardian_id,
        'sequence_order': sequence_order,
        'public_key': public_key,
        'coefficient_commitments': [public_key],  # Simplified
        'backups': {}
    }

    # Create election public key structure (simplified)
    election_public_key = {
        'owner_id': guardian_id,
        'sequence_order': sequence_order,
        'key': public_key,
        'coefficient_commitments': [public_key]
    }

    return {
        'guardian_id': guardian_id,
        'sequence_order': sequence_order,
        'guardian_data': guardian_data,
        'election_public_key': election_public_key,
        'number_of_guardians': number_of_guardians,
        'quorum': quorum
    }


@app.route('/setup_guardian', methods=['POST'])
def api_setup_guardian():
    """API endpoint to setup a single guardian by accepting only public key."""
    try:
        print('🔥 setup_guardian endpoint called!')
        data = request.json
        print(f'📦 Received data: {json.dumps(data, indent=2)}')

        # Extract and validate required fields
        required_fields = ['guardian_id', 'sequence_order', 'public_key',
                           'number_of_guardians', 'quorum', 'party_names', 'candidate_names']
        for field in required_fields:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'}), 400

        guardian_id = data['guardian_id']
        sequence_order = int(data['sequence_order'])
        public_key = data['public_key']
        number_of_guardians = int(data['number_of_guardians'])
        quorum = int(data['quorum'])
        party_names = data['party_names']
        candidate_names = data['candidate_names']

        print(
            f'✅ Parsed inputs: guardian_id={guardian_id}, sequence_order={sequence_order}')

        # Call service function
        result = minimal_setup_guardian_service(
            guardian_id,
            sequence_order,
            public_key,
            number_of_guardians,
            quorum,
            party_names,
            candidate_names
        )

        print('✅ Service function completed successfully')

        # Format response according to your API specification
        response = {
            'status': 'success',
            'guardian_id': result['guardian_id'],
            'sequence_order': result['sequence_order'],
            'guardian_data': json.dumps(result['guardian_data']),
            'election_public_key': json.dumps(result['election_public_key']),
            'number_of_guardians': result['number_of_guardians'],
            'quorum': result['quorum']
        }

        print(f'✅ Sending response: {json.dumps(response, indent=2)}')

        # Security check: ensure no private keys in response
        response_str = json.dumps(response).lower()
        if 'private_key' in response_str:
            print('❌ SECURITY WARNING: private_key found in response!')
        else:
            print('✅ SECURITY: No private keys in response')

        return jsonify(response), 200

    except KeyError as e:
        error_msg = f'Missing required field: {str(e)}'
        print(f'❌ KeyError: {error_msg}')
        return jsonify({'status': 'error', 'message': error_msg}), 400
    except ValueError as e:
        error_msg = f'Invalid value: {str(e)}'
        print(f'❌ ValueError: {error_msg}')
        return jsonify({'status': 'error', 'message': error_msg}), 400
    except Exception as e:
        error_msg = f'Internal server error: {str(e)}'
        print(f'❌ Exception: {error_msg}')
        return jsonify({'status': 'error', 'message': error_msg}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'endpoint': 'setup_guardian',
        'version': 'minimal_working'
    }), 200


@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        'message': 'ElectionGuard API - setup_guardian endpoint',
        'available_endpoints': [
            'GET /',
            'GET /health',
            'POST /setup_guardian'
        ],
        'status': 'running'
    }), 200


if __name__ == '__main__':
    print("🚀 Starting MINIMAL WORKING API server...")
    print("📡 Server will run on http://localhost:5000")
    print("🎯 Available endpoints:")
    print("   - GET / (info)")
    print("   - GET /health (health check)")
    print("   - POST /setup_guardian (main endpoint)")
    print("")
    print("✅ This version has NO heavy dependencies!")
    print("✅ It will work immediately!")

    app.run(host='0.0.0.0', port=5000, debug=True)
