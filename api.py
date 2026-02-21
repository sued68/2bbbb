from flask import Flask, jsonify, request, render_template
from bingo_db import (
    get_cardboard_as_grid,
    get_called_numbers,
    check_card_winner,
    handle_winner,
    get_user_id,
    buy_card,
    get_all_cards_with_status
)

app = Flask(__name__)

# ========== WEB PAGES ==========
@app.route('/')
def serve_webapp():
    """Serve the main card viewer (used with ?card=id)."""
    return render_template('card.html')

@app.route('/shop')
def shop():
    """Serve the shop page where users can browse and buy cards."""
    return render_template('shop.html')

# ========== API ENDPOINTS ==========
@app.route('/api/card/<int:card_id>')
def get_card(card_id):
    """Return the 5x5 grid for the given card ID."""
    grid = get_cardboard_as_grid(card_id)
    if grid:
        return jsonify(grid)
    return jsonify({"error": "Card not found"}), 404

@app.route('/api/cards/available')
def available_cards():
    """Return a list of all card IDs that are not yet taken in the current round."""
    cards = get_all_cards_with_status()
    available = [{"id": c["id"]} for c in cards if not c["taken"]]
    return jsonify(available)

@app.route('/api/buy', methods=['POST'])
def purchase_card():
    """
    Purchase a card.
    Expected JSON: { "telegram_id": 123456789, "card_id": 42 }
    """
    data = request.json
    telegram_id = data.get('telegram_id')
    card_id = data.get('card_id')

    if not telegram_id or not card_id:
        return jsonify({"success": False, "message": "Missing telegram_id or card_id"}), 400

    success, message = buy_card(telegram_id, card_id)
    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "message": message}), 400

@app.route('/api/win', methods=['POST'])
def claim_win():
    """
    (Optional) Alternative endpoint for win claims directly from the web app.
    Expected JSON: { "user_id": 123456, "card_id": 42 }
    """
    data = request.json
    user_id = data.get('user_id')
    card_id = data.get('card_id')
    if not user_id or not card_id:
        return jsonify({"error": "Missing user_id or card_id"}), 400

    # Optional: verify user owns this card (you could add a function)
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