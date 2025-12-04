#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from app import create_app
load_dotenv()

db_dir = 'C:/temp/yeastar' if os.name == 'nt' else '/tmp/yeastar'
os.makedirs(db_dir, exist_ok=True)
os.environ['DATABASE_URL'] = f'sqlite:///{db_dir}/app.db'

app = create_app()

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    print("=" * 60)
    print("Yeastar Presence Manager")
    print("=" * 60)
    print(f"Server running on: http://{host}:{port}")
    print(f"Debug mode: {debug}")
    print("=" * 60)
    print("\nPress CTRL+C to stop the server\n")

    app.run(host=host, port=port, debug=debug)
