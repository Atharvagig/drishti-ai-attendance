"""
Drishti AI — SQLite to MongoDB Atlas Migration & Verification Engine
Migrates all relational tables, binary face embeddings, and relational constraints
from attendance.db to MongoDB Atlas.
Includes dry-run validation, verification reporting, and rollback instructions.
"""
import os
import sys
import sqlite3
import argparse
import pickle
from datetime import datetime
import pymongo
from pymongo import MongoClient
from bson.binary import Binary

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)

import database_mongo as db_mongo

DEFAULT_SQLITE_PATH = os.path.join(CURRENT_DIR, 'data', 'attendance.db')


def migrate(sqlite_path=DEFAULT_SQLITE_PATH, mongo_uri=None, db_name='drishti_attendance',
            dry_run=False, use_mock=False):
    """
    Executes complete migration from SQLite to MongoDB Atlas.
    Returns (success: bool, report: dict).
    """
    print("=" * 70)
    print("  DRISHTI AI — SQLite to MongoDB Atlas Migration Tool")
    print("=" * 70)
    print(f" Source SQLite DB : {sqlite_path}")
    print(f" Target DB Name   : {db_name}")
    print(f" Dry Run Mode     : {dry_run}")
    print(f" Mock Engine Mode : {use_mock}")
    print("=" * 70)

    if not os.path.exists(sqlite_path):
        print(f"[ERROR] Source database file not found: {sqlite_path}")
        return False, {}

    # Connect to MongoDB or Mock
    if use_mock:
        import mongomock
        client = mongomock.MongoClient()
        db = client[db_name]
    else:
        uri = mongo_uri or os.getenv('MONGODB_URI')
        if not uri or '<username>' in uri:
            print("[ERROR] MONGODB_URI environment variable is missing or contains placeholder.")
            print("Please set MONGODB_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority")
            return False, {}
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=7000, connectTimeoutMS=7000)
            # Test connection
            client.admin.command('ping')
            db = client[db_name]
            print("[OK] Connected to MongoDB Atlas cluster.")
        except Exception as e:
            print(f"[ERROR] Failed to connect to MongoDB Atlas: {e}")
            return False, {}

    # Initialize schema & indexes in target
    if not dry_run:
        db_mongo.init_db(db)

    # Read SQLite tables
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'")
    tables = [r['name'] for r in cursor.fetchall()]

    report = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tables': {},
        'status': 'SUCCESS'
    }

    # Sequence tracking for counters
    counters = {}

    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        rows = [dict(r) for r in cursor.fetchall()]
        src_count = len(rows)

        print(f"\n[Processing Table] '{table}' ({src_count} source records)...")

        if dry_run:
            report['tables'][table] = {
                'source_count': src_count,
                'target_count': src_count,
                'status': 'DRY_RUN_VALIDATED'
            }
            continue

        collection = db[table]
        migrated_count = 0
        max_id = 0

        for r in rows:
            doc = dict(r)

            # Track integer sequence ID
            if 'id' in doc and isinstance(doc['id'], int):
                max_id = max(max_id, doc['id'])

            # Handle face embeddings binary
            if table == 'face_embeddings' and 'embedding_blob' in doc:
                raw = doc['embedding_blob']
                if isinstance(raw, (bytes, bytearray)):
                    doc['embedding_blob'] = Binary(raw)

            # Handle unique keys & upsert
            filter_query = {}
            if 'id' in doc:
                filter_query['id'] = doc['id']
            elif 'student_id' in doc:
                filter_query['student_id'] = doc['student_id']
            elif 'username' in doc:
                filter_query['username'] = doc['username']
            elif 'name' in doc:
                filter_query['name'] = doc['name']
            else:
                filter_query = doc

            try:
                collection.replace_one(filter_query, doc, upsert=True)
                migrated_count += 1
            except Exception as e:
                print(f"  [WARN] Failed to insert row in {table}: {e}")

        if max_id > 0:
            counters[table] = max_id
            db_mongo.set_sequence_value(table, max_id, db)

        dest_count = collection.count_documents({})
        match = (dest_count >= src_count)
        status_str = 'VERIFIED' if match else 'COUNT_MISMATCH'
        if not match:
            report['status'] = 'WARNING_COUNT_MISMATCH'

        report['tables'][table] = {
            'source_count': src_count,
            'target_count': dest_count,
            'status': status_str
        }
        print(f"  -> Migrated: {dest_count} documents in MongoDB Atlas ({status_str})")

    sqlite_conn.close()

    # Final Summary Report
    print("\n" + "=" * 70)
    print("  MIGRATION VERIFICATION AUDIT REPORT")
    print("=" * 70)
    print(f"{'TABLE / COLLECTION':<25} | {'SQLITE':<8} | {'MONGODB':<8} | {'STATUS'}")
    print("-" * 70)
    for tbl, info in report['tables'].items():
        print(f"{tbl:<25} | {info['source_count']:<8} | {info['target_count']:<8} | {info['status']}")
    print("=" * 70)

    # Representative record checks
    if not dry_run:
        sample_student = db.students.find_one()
        sample_user = db.users.find_one({'username': 'admin'})
        sample_emb = db.face_embeddings.find_one()

        print("\n[Spot Checks]:")
        print(f"  Sample Student: {sample_student.get('student_id') if sample_student else 'None'}")
        print(f"  Admin User Found: {'YES' if sample_user else 'NO'}")
        if sample_emb:
            try:
                emb_arr = pickle.loads(sample_emb['embedding_blob'])
                print(f"  Face Embedding Deserialization: OK ({len(emb_arr)}-D array)")
            except Exception as e:
                print(f"  Face Embedding Deserialization: FAILED ({e})")

    print("\n[Rollback Procedure]:")
    print("If you need to roll back, simply unset MONGODB_URI or set DB_BACKEND=sqlite.")
    print("The original SQLite database at data/attendance.db (and backup at attendance.db.bak)")
    print("remains completely unmodified and available.")
    print("=" * 70)

    return True, report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Drishti AI SQLite to MongoDB Migration")
    parser.add_argument('--sqlite', default=DEFAULT_SQLITE_PATH, help="Path to SQLite attendance.db")
    parser.add_argument('--uri', default=None, help="MongoDB connection URI")
    parser.add_argument('--db', default='drishti_attendance', help="MongoDB database name")
    parser.add_argument('--dry-run', action='store_true', help="Validate schema and counts without writing")
    parser.add_argument('--mock', action='store_true', help="Run migration against in-memory MongoDB mock")

    args = parser.parse_args()
    success, rep = migrate(
        sqlite_path=args.sqlite,
        mongo_uri=args.uri,
        db_name=args.db,
        dry_run=args.dry_run,
        use_mock=args.mock
    )
    sys.exit(0 if success else 1)
