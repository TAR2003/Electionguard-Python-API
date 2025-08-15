#!/usr/bin/env python3
"""
Simplified API to test the setup_guardian endpoint specifically.
"""

from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Simulate the service response for testing


def mock_setup_guardian_service(guardian_id, sequence_order, public_key, number_of_guardians, quorum, party_names, candidate_names):
    """Mock service that returns a simple response"""
    return {
        'guardian_id': guardian_id,
        'sequence_order': sequence_order,
        'guardian_data': {
            'id': guardian_id,
            'sequence_order': sequence_order,
            'public_key': public_key
        },
        'election_public_key': {
            'owner_id': guardian_id,
            'key': public_key
        },
        'number_of_guardians': number_of_guardians,
        'quorum': quorum
    }


@app.route('/setup_guardian', methods=['POST'])
def api_setup_guardian():
    """Simplified API endpoint to test setup_guardian"""
    try:
        print('🔥 setup_guardian endpoint called!')
        data = request.json
        print(f'📦 Received data: {json.dumps(data, indent=2)}')

        guardian_id = data['guardian_id']
        sequence_order = int(data['sequence_order'])
        public_key = data['public_key']
        number_of_guardians = int(data['number_of_guardians'])
        quorum = int(data['quorum'])
        party_names = data['party_names']
        candidate_names = data['candidate_names']

        # Call mock service function
        result = mock_setup_guardian_service(
            guardian_id,
            sequence_order,
            public_key,
            number_of_guardians,
            quorum,
            party_names,
            candidate_names
        )

        response = {
            'status': 'success',
            'guardian_id': result['guardian_id'],
            'sequence_order': result['sequence_order'],
            'guardian_data': json.dumps(result['guardian_data']),
            'election_public_key': json.dumps(result['election_public_key']),
            'number_of_guardians': result['number_of_guardians'],
            'quorum': result['quorum']
        }

        print(f'✅ Response: {json.dumps(response, indent=2)}')
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
    return jsonify({'status': 'healthy', 'endpoint': 'setup_guardian', 'version': 'simplified'}), 200


if __name__ == '__main__':
    print("🚀 Starting SIMPLIFIED API server for testing setup_guardian endpoint...")
    print("📡 Server will run on http://localhost:5000")
    print("🎯 Available endpoints:")
    print("   - POST /setup_guardian")
    print("   - GET /health")

    app.run(host='0.0.0.0', port=5000, debug=True)
