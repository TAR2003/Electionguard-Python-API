"""
Example integration with your existing ElectionGuard API.

This shows how to modify your existing API endpoints to use the ballot sanitization.
"""

from flask import Flask, request, jsonify
from ballot_publisher import BallotPublisher
import json

app = Flask(__name__)

# Initialize the ballot publisher
ballot_publisher = BallotPublisher()

# Your existing encrypted ballot creation endpoint (modified)
@app.route('/api/create_encrypted_ballot', methods=['POST'])
def create_encrypted_ballot():
    """
    Your existing endpoint, but now with secure publication logic.
    """
    try:
        # Your existing ballot creation logic here
        # ... (ballot creation code) ...
        
        # For demonstration, let's assume you have the encrypted ballot response
        # In your real implementation, this would come from your ballot encryption process
        
        request_data = request.get_json()
        ballot_id = request_data.get('ballot_id', 'generated-ballot-id')
        ballot_status = request_data.get('ballot_status', 'CAST')  # Default to CAST
        
        # Load your encrypted ballot response (in real implementation, this comes from your encryption)
        with open("create_encrypted_ballot_response.json", "r") as f:
            encrypted_ballot_response = f.read()
        
        # Publish the ballot securely based on status
        publication_result = ballot_publisher.publish_ballot(
            ballot_id=ballot_id,
            encrypted_ballot_response=encrypted_ballot_response,
            ballot_status=ballot_status
        )
        
        return jsonify(publication_result), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ballots/<ballot_id>', methods=['GET'])
def get_published_ballot(ballot_id):
    """
    Retrieve a published ballot (sanitized based on its status).
    """
    try:
        ballot = ballot_publisher.get_published_ballot(ballot_id)
        if ballot:
            return jsonify(ballot), 200
        return jsonify({"error": "Ballot not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ballots/<ballot_id>/nonces', methods=['GET'])
def get_ballot_nonces(ballot_id):
    """
    Get nonces for a ballot (only available for audited ballots).
    """
    try:
        nonces = ballot_publisher.get_ballot_nonces(ballot_id)
        if nonces:
            return jsonify({
                "ballot_id": ballot_id, 
                "nonces": nonces,
                "status": "AUDITED"
            }), 200
        
        # Check if ballot exists but is cast (no nonces available)
        ballot = ballot_publisher.get_published_ballot(ballot_id)
        if ballot and not ballot.get('nonces_available', False):
            return jsonify({
                "error": "Nonces not available for cast ballots", 
                "ballot_status": "CAST"
            }), 403
        
        return jsonify({"error": "Ballot not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ballots', methods=['GET'])
def list_published_ballots():
    """
    List all published ballots with their publication status.
    """
    try:
        status_filter = request.args.get('status')  # Optional: 'CAST' or 'AUDITED'
        ballots = ballot_publisher.list_published_ballots(status_filter)
        
        # Add summary statistics
        stats = ballot_publisher.get_publication_stats()
        
        return jsonify({
            "ballots": ballots,
            "statistics": stats
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/publish_ballot', methods=['POST'])
def publish_existing_ballot():
    """
    Endpoint to publish an already created encrypted ballot.
    """
    try:
        data = request.get_json()
        
        ballot_id = data.get('ballot_id')
        encrypted_ballot_response = data.get('encrypted_ballot_response')  
        ballot_status = data.get('ballot_status')
        
        if not all([ballot_id, encrypted_ballot_response, ballot_status]):
            return jsonify({"error": "Missing required fields: ballot_id, encrypted_ballot_response, ballot_status"}), 400
        
        result = ballot_publisher.publish_ballot(
            ballot_id=ballot_id,
            encrypted_ballot_response=encrypted_ballot_response,
            ballot_status=ballot_status
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/audit_ballot/<ballot_id>', methods=['POST'])
def mark_ballot_for_audit(ballot_id):
    """
    Mark a cast ballot for audit (this would republish it with nonces).
    Note: This is a simplified example - in practice you'd need more complex logic.
    """
    try:
        # This is a simplified example
        # In practice, you'd need to:
        # 1. Verify the ballot exists and is currently cast
        # 2. Have the original encrypted ballot response stored
        # 3. Re-publish with AUDITED status
        
        return jsonify({"message": "Audit functionality would be implemented here"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    stats = ballot_publisher.get_publication_stats()
    return jsonify({
        "status": "healthy",
        "service": "ElectionGuard Ballot Publisher",
        "statistics": stats
    }), 200


if __name__ == '__main__':
    print("=== ElectionGuard API with Secure Ballot Publication ===")
    print("\nAvailable endpoints:")
    print("  POST /api/create_encrypted_ballot - Create and publish encrypted ballot")
    print("  POST /api/publish_ballot - Publish existing encrypted ballot")
    print("  GET  /api/ballots/<id> - Get published ballot")
    print("  GET  /api/ballots/<id>/nonces - Get ballot nonces (audited only)")
    print("  GET  /api/ballots?status=CAST|AUDITED - List ballots")
    print("  GET  /api/health - Health check")
    print("\nSecurity Features:")
    print("  ✓ Nonces removed from cast ballots")
    print("  ✓ Nonces available for audited ballots")
    print("  ✓ Secure separation of ballot data and nonces")
    print("  ✓ Proper access control for nonce retrieval")
    
    # Run the Flask app
    app.run(debug=True, port=5000)
