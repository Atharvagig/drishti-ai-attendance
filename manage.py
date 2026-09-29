"""
Drishti AI — Management CLI
Run from the project root or backend/ directory.

Usage:
    python manage.py create-admin
    python manage.py create-user
    python manage.py list-users
    python manage.py reset-password <username>
    python manage.py unlock <username>
    python manage.py migrate
"""
import sys
import os
import getpass
import argparse

# Ensure backend/ is on the path
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
if not os.path.exists(os.path.join(BACKEND_DIR, 'database.py')):
    # If running from inside backend/
    BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

import database


def cmd_create_admin():
    """Interactively create a super_admin user."""
    print("\n=== Create Super Admin ===")
    username  = input("Username [admin]: ").strip() or 'admin'
    full_name = input("Full Name [Administrator]: ").strip() or 'Administrator'
    email     = input("Email [admin@drishti.ai]: ").strip() or 'admin@drishti.ai'

    while True:
        password = getpass.getpass("Password (min 8 chars): ")
        confirm  = getpass.getpass("Confirm Password: ")
        if password != confirm:
            print("Passwords do not match. Try again.")
            continue
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            continue
        break

    database.init_db()
    database.seed_defaults()

    # Check if username exists
    existing = database.get_user_by_username(username)
    if existing:
        choice = input(f"User '{username}' already exists. Update role to super_admin? [y/N]: ")
        if choice.lower() == 'y':
            database.update_user(existing['id'], role='super_admin',
                                 full_name=full_name, email=email)
            database.reset_user_password(existing['id'], password)
            print(f"\n✓ Updated '{username}' to super_admin.")
        else:
            print("Aborted.")
        return

    user_id = database.create_user(
        username=username,
        password=password,
        role='super_admin',
        full_name=full_name,
        email=email,
    )
    print(f"\n✓ Super admin '{username}' created (ID: {user_id}).")
    print("  You can now log in at http://localhost:5000/login")


def cmd_create_user():
    """Interactively create any user."""
    print("\n=== Create User ===")
    username  = input("Username: ").strip()
    full_name = input("Full Name: ").strip()
    email     = input("Email: ").strip()

    valid_roles = ['super_admin', 'department_head', 'faculty', 'attendance_operator', 'student']
    print(f"Roles: {', '.join(valid_roles)}")
    role = input("Role: ").strip()
    if role not in valid_roles:
        print(f"Invalid role: {role}")
        return

    dept_id = input("Department ID (leave blank for none): ").strip() or None
    if dept_id:
        dept_id = int(dept_id)

    while True:
        password = getpass.getpass("Password (min 8 chars): ")
        confirm  = getpass.getpass("Confirm Password: ")
        if password != confirm:
            print("Passwords do not match. Try again.")
            continue
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            continue
        break

    database.init_db()
    database.seed_defaults()

    try:
        user_id = database.create_user(
            username=username,
            password=password,
            role=role,
            full_name=full_name,
            email=email,
            department_id=dept_id,
        )
        print(f"\n✓ User '{username}' created (ID: {user_id}, Role: {role}).")
    except Exception as e:
        print(f"Error: {e}")


def cmd_list_users():
    """List all users in the system."""
    database.init_db()
    users = database.get_all_users()
    if not users:
        print("No users found.")
        return
    print(f"\n{'ID':<5} {'Username':<20} {'Role':<20} {'Active':<8} {'Last Login'}")
    print("-" * 70)
    for u in users:
        active    = "Yes" if u.get('is_active') else "No"
        last_login = u.get('last_login', 'Never') or 'Never'
        print(f"{u['id']:<5} {u['username']:<20} {u['role']:<20} {active:<8} {last_login}")


def cmd_reset_password(username):
    """Reset a user's password."""
    database.init_db()
    user = database.get_user_by_username(username)
    if not user:
        print(f"User '{username}' not found.")
        return

    while True:
        password = getpass.getpass(f"New password for '{username}' (min 8 chars): ")
        confirm  = getpass.getpass("Confirm Password: ")
        if password != confirm:
            print("Passwords do not match. Try again.")
            continue
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            continue
        break

    database.reset_user_password(user['id'], password)
    print(f"✓ Password reset for '{username}'.")


def cmd_unlock(username):
    """Unlock a locked user account."""
    database.init_db()
    user = database.get_user_by_username(username)
    if not user:
        print(f"User '{username}' not found.")
        return
    database.unlock_user(user['id'])
    print(f"✓ Account '{username}' unlocked.")


def cmd_migrate():
    """Run safe database migrations."""
    print("Running database initialization and migrations...")
    database.init_db()
    database.seed_defaults()
    print("✓ Migration complete.")


def main():
    parser = argparse.ArgumentParser(
        description='Drishti AI Management CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  create-admin           Create or update the super_admin user
  create-user            Create a new user interactively
  list-users             List all users
  reset-password <user>  Reset a user's password
  unlock <username>      Unlock a locked account
  migrate                Run database migrations
        """
    )
    parser.add_argument('command', choices=[
        'create-admin', 'create-user', 'list-users',
        'reset-password', 'unlock', 'migrate'
    ])
    parser.add_argument('arg', nargs='?', help='Argument for the command (e.g. username)')

    args = parser.parse_args()

    if args.command == 'create-admin':
        cmd_create_admin()
    elif args.command == 'create-user':
        cmd_create_user()
    elif args.command == 'list-users':
        cmd_list_users()
    elif args.command == 'reset-password':
        if not args.arg:
            print("Usage: python manage.py reset-password <username>")
            sys.exit(1)
        cmd_reset_password(args.arg)
    elif args.command == 'unlock':
        if not args.arg:
            print("Usage: python manage.py unlock <username>")
            sys.exit(1)
        cmd_unlock(args.arg)
    elif args.command == 'migrate':
        cmd_migrate()


if __name__ == '__main__':
    main()
