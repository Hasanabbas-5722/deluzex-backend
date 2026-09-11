import sys
from app.core.database import db

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage:")
        print("  python make_admin.py <email>           (Grants admin rights)")
        print("  python make_admin.py <email> --revoke  (Revokes admin rights)")
        print("  python make_admin.py --list            (Lists all users and their status)\n")
        print("Current users:")
        for u in db.users.find({}, {"email": 1, "first_name": 1, "last_name": 1, "is_admin": 1}):
            status = "ADMIN" if u.get("is_admin") else "User"
            name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
            print(f"  [{status:5}] {u.get('email')} ({name})")
        return

    if args[0] == "--list":
        print("Users in database:")
        for u in db.users.find({}, {"email": 1, "first_name": 1, "last_name": 1, "is_admin": 1}):
            status = "ADMIN" if u.get("is_admin") else "User"
            name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
            print(f"  [{status:5}] {u.get('email')} ({name})")
        return

    email = args[0].strip()
    revoke = "--revoke" in args

    user = db.users.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}})
    if not user:
        print(f"Error: No user found with email '{email}'.")
        return

    target_status = not revoke
    db.users.update_one({"_id": user["_id"]}, {"$set": {"is_admin": target_status}})

    action = "revoked from" if revoke else "granted to"
    print(f"Success: Admin privileges {action} {user.get('email')}.")

if __name__ == "__main__":
    main()
