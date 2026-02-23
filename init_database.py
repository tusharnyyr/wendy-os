"""
Initialize database by creating all tables for Wendy.
Run this script once to set up the database schema.
"""
from database import init_db

if __name__ == "__main__":
    print("Creating database tables for Wendy...")
    init_db()
    print("✅ Database initialized successfully!")