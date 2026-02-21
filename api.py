from flask import Flask, jsonify, request, render_template
from bingo_db import get_cardboard_as_grid, get_called_numbers, check_card_winner, handle_winner, get_user_id

app = Flask(__name__)

@app.route('/')
def serve_webapp():
    """Serve the web app HTML page."""
    return render_template('card.html')

@app.route('/api/card/<int:card_id>')
def get_card(card_id):
    """Return the 5x5 grid for the given card ID."""
    grid = get_cardboard_as_grid(card_id)
    if grid:
        return jsonify(grid)
    return jsonify({"error": "Card not found"}), 404

@app.route('/api/win', methods=['POST'])
def claim_win():
    """
    Alternative endpoint: web app can POST directly here.
    Expected JSON: { "user_id": 123456, "card_id": 42 }
    """
    data = request.json
    user_id = data.get('user_id')
    card_id = data.get('card_id')
    if not user_id or not card_id:
        return jsonify({"error": "Missing user_id or card_id"}), 400

    # Optional: verify user owns this card (you'd need a function)
    # For simplicity, we skip ownership check here.

    called = get_called_numbers()
    card = get_cardboard_as_grid(card_id)
    if not card:
        return jsonify({"error": "Invalid card"}), 404

    if check_card_winner(card, called):
        result = handle_winner(user_id)
        return jsonify({"message": result})
    else:
        return jsonify({"error": "Not a winner yet"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)