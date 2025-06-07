import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_heroku import app

if __name__ == "__main__":
    app.run()
