import threading
from api import app
from bot import main as bot_main

if __name__ == "__main__":
    # Start the bot in a background thread
    bot_thread = threading.Thread(target=bot_main, daemon=True)
    bot_thread.start()
    # Run Flask
    app.run(host="0.0.0.0", port=5000)