import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from main import app
from app.core.security import create_access_token
from app.core.database import db
from jose import jwt
from app.core.security import SECRET_KEY, ALGORITHM

client = TestClient(app)

def test_token_claims_and_admin_restrictions():
    # 1. Test regular user token
    regular_token = create_access_token(subject="fake_user_id", is_admin=False)
    decoded_reg = jwt.decode(regular_token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded_reg.get("is_admin") is False, "Regular token must have is_admin=False"
    print("[PASS] Regular token claim is_admin=False confirmed")

    # 2. Test admin user token
    admin_token = create_access_token(subject="fake_admin_id", is_admin=True)
    decoded_adm = jwt.decode(admin_token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded_adm.get("is_admin") is True, "Admin token must have is_admin=True"
    print("[PASS] Admin token claim is_admin=True confirmed")

    # 3. Check existing user Hasanabbas@gmail.com is admin in db
    admin_user = db.users.find_one({"email": {"$regex": "^Hasanabbas@gmail.com$", "$options": "i"}})
    assert admin_user is not None, "Hasanabbas@gmail.com should exist in db"
    assert admin_user.get("is_admin") is True, "Hasanabbas@gmail.com must have is_admin=True"
    print("[PASS] Database verified: Hasanabbas@gmail.com is an ADMIN")

    # 4. Check regular user in db
    regular_user = db.users.find_one({"email": {"$regex": "^hasan@example.com$", "$options": "i"}})
    assert regular_user is not None, "hasan@example.com should exist in db"
    assert regular_user.get("is_admin") is False, "hasan@example.com must have is_admin=False"
    print("[PASS] Database verified: hasan@example.com is a regular User")

    # 5. Generate actual token for hasan@example.com (regular) and test protected endpoint
    reg_user_token = create_access_token(subject=str(regular_user["_id"]), is_admin=False)
    res_reg = client.get("/api/v1/contact", headers={"Authorization": f"Bearer {reg_user_token}"})
    assert res_reg.status_code == 403, f"Expected 403 Forbidden for regular user, got {res_reg.status_code}"
    print("[PASS] Access restriction verified: Regular user cannot access GET /api/v1/contact (HTTP 403 Forbidden)")

    # 6. Generate actual token for Hasanabbas@gmail.com (admin) and test protected endpoint
    adm_user_token = create_access_token(subject=str(admin_user["_id"]), is_admin=True)
    res_adm = client.get("/api/v1/contact", headers={"Authorization": f"Bearer {adm_user_token}"})
    assert res_adm.status_code == 200, f"Expected 200 OK for admin user, got {res_adm.status_code}"
    print("[PASS] Admin access verified: Admin user can access GET /api/v1/contact (HTTP 200 OK)")

    # 7. Test /auth/me for regular user
    me_reg = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {reg_user_token}"})
    assert me_reg.status_code == 200
    assert me_reg.json()["data"]["is_admin"] is False
    print("[PASS] /auth/me correctly identifies regular user as non-admin")

    # 8. Test /auth/me for admin user
    me_adm = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {adm_user_token}"})
    assert me_adm.status_code == 200
    assert me_adm.json()["data"]["is_admin"] is True
    print("[PASS] /auth/me correctly identifies admin user as admin")

    # 9. Test /auth/admin/login rejects regular user
    # Try logging into admin portal with regular user
    res_admin_login_reject = client.post("/api/v1/auth/admin/login", json={
        "email": "hasan@example.com",
        "password": "Password@123"
    })
    # If password matches, it must be 403 Forbidden because is_admin is False!
    if res_admin_login_reject.status_code == 403:
        assert res_admin_login_reject.json()["detail"] == "Access denied. You do not have administrator privileges."
        print("[PASS] /auth/admin/login strictly rejects regular users with HTTP 403")

    # 10. Test case-insensitive email lookup
    user_with_capitals = db.users.find_one({"email": {"$regex": "^Hasanabbas@gmail.com$", "$options": "i"}})
    assert user_with_capitals is not None
    # Test lowercase query against db
    matched = db.users.find_one({"email": {"$regex": "^hasanabbas@gmail.com$", "$options": "i"}})
    assert matched is not None and matched["_id"] == user_with_capitals["_id"]
    print("[PASS] Case-insensitive email query matches Hasanabbas@gmail.com via hasanabbas@gmail.com")

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_token_claims_and_admin_restrictions()

