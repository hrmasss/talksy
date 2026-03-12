"""Create a superuser account via command line."""

import asyncio
import getpass
import hashlib
import re
import secrets
import sys
from pathlib import Path
from uuid import uuid4

# Load .env from project root before importing app modules
_project_root = Path(__file__).resolve().parents[4]  # talksy root
_env_file = _project_root / ".env"
if _env_file.exists():
    from dotenv import load_dotenv  # noqa: E402

    load_dotenv(_env_file)

from app.db.tables import User, UserRole  # noqa: E402


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}${hashed}"


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    return True, ""


async def create_superuser(
    email: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
    interactive: bool = True,
) -> bool:
    """Create a superuser account.
    
    Args:
        email: User email (prompted if not provided in interactive mode)
        password: User password (prompted if not provided in interactive mode)
        full_name: User full name (prompted if not provided in interactive mode)
        interactive: Whether to prompt for missing values
        
    Returns:
        True if superuser was created successfully.
    """
    from app.db.bootstrap import ensure_tables_exist
    
    # Ensure database tables exist
    await ensure_tables_exist()
    
    # Get email
    if not email:
        if not interactive:
            print("Error: Email is required in non-interactive mode")
            return False
        while True:
            email = input("Email: ").strip()
            if validate_email(email):
                break
            print("Invalid email format. Please try again.")
    
    # Check if user exists
    existing = await User.select().where(User.email == email.lower()).first()
    if existing:
        if existing.get("role") == UserRole.ADMIN.value:
            print(f"Superuser with email '{email}' already exists.")
            return False
        else:
            # Upgrade existing user to admin
            if interactive:
                upgrade = input(f"User '{email}' exists. Upgrade to admin? [y/N]: ").strip().lower()
                if upgrade != 'y':
                    print("Aborted.")
                    return False
            await User.update({User.role: UserRole.ADMIN.value}).where(User.email == email.lower())
            print(f"User '{email}' upgraded to admin successfully!")
            return True
    
    # Get full name
    if not full_name:
        if not interactive:
            full_name = "Admin"
        else:
            full_name = input("Full name: ").strip()
            if not full_name:
                full_name = "Admin"
    
    # Get password
    if not password:
        if not interactive:
            print("Error: Password is required in non-interactive mode")
            return False
        while True:
            password = getpass.getpass("Password: ")
            valid, error = validate_password(password)
            if not valid:
                print(f"Invalid password: {error}")
                continue
            password_confirm = getpass.getpass("Password (confirm): ")
            if password != password_confirm:
                print("Passwords do not match. Please try again.")
                continue
            break
    else:
        valid, error = validate_password(password)
        if not valid:
            print(f"Invalid password: {error}")
            return False
    
    # Create user
    user_data = {
        "id": uuid4(),
        "email": email.lower(),
        "password_hash": hash_password(password),
        "full_name": full_name,
        "role": UserRole.ADMIN.value,
        "is_active": True,
        "is_verified": True,
    }
    
    user = User(**user_data)
    await user.save()
    
    print("\nSuperuser created successfully!")
    print(f"  Email: {email}")
    print(f"  Name: {full_name}")
    print("  Role: admin")
    
    return True


def main():
    """CLI entry point for createsuperuser."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a superuser account")
    parser.add_argument("--email", "-e", help="User email")
    parser.add_argument("--password", "-p", help="User password")
    parser.add_argument("--name", "-n", help="User full name")
    parser.add_argument(
        "--no-input",
        action="store_true",
        help="Run in non-interactive mode (requires --email and --password)",
    )
    
    args = parser.parse_args()
    
    success = asyncio.run(
        create_superuser(
            email=args.email,
            password=args.password,
            full_name=args.name,
            interactive=not args.no_input,
        )
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
