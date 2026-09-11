import sys
import os
sys.path.insert(0, os.path.abspath("."))

from starlette.testclient import TestClient
from main import app
from app.core.security import create_access_token
from app.core.database import db

client = TestClient(app)

def test_hero_products_crud():
    reg_user = db.users.find_one({"email": {"$regex": "^hasan@example.com$", "$options": "i"}})
    adm_user = db.users.find_one({"email": {"$regex": "^Hasanabbas@gmail.com$", "$options": "i"}})
    assert reg_user and adm_user

    # 1. Get hero products (should auto-seed if empty and return at least 3)
    res = client.get("/api/v1/hero-products")
    assert res.status_code == 200, f"GET failed: {res.text}"
    items = res.json()
    assert isinstance(items, list)
    assert len(items) >= 3, f"Expected at least 3 hero items, got {len(items)}"
    print(f"[PASS] GET /api/v1/hero-products returned {len(items)} items")

    # 2. Test unauthorized create (regular user)
    reg_token = create_access_token(subject=str(reg_user["_id"]), is_admin=False)
    res_unauth = client.post(
        "/api/v1/hero-products",
        data={"name": "Test Lamp", "price": "199", "alt": "Test Lamp Alt", "image": "/images/test.jpg"},
        headers={"Authorization": f"Bearer {reg_token}"}
    )
    assert res_unauth.status_code == 403, f"Expected 403, got {res_unauth.status_code}"
    print("[PASS] Non-admin cannot create hero product (HTTP 403 Forbidden)")

    # 3. Test admin create
    adm_token = create_access_token(subject=str(adm_user["_id"]), is_admin=True)
    res_create = client.post(
        "/api/v1/hero-products",
        data={"name": "New Luxury Lamp", "price": "450", "alt": "Luxury modern lamp", "image": "/images/lamp_modern_tall_1784107732736.jpg"},
        headers={"Authorization": f"Bearer {adm_token}"}
    )
    assert res_create.status_code == 200, f"Create failed: {res_create.text}"
    created = res_create.json()
    assert created["name"] == "New Luxury Lamp"
    assert created["price"] == 450.0
    item_id = str(created.get("_id") or created.get("id"))
    print(f"[PASS] Admin created hero product: {item_id}")

    # 4. Test admin update
    res_update = client.put(
        f"/api/v1/hero-products/{item_id}",
        data={"name": "Updated Luxury Lamp", "price": "499"},
        headers={"Authorization": f"Bearer {adm_token}"}
    )
    assert res_update.status_code == 200, f"Update failed: {res_update.text}"
    updated = res_update.json()
    assert updated["name"] == "Updated Luxury Lamp"
    assert updated["price"] == 499.0
    print(f"[PASS] Admin updated hero product successfully")

    # 5. Test admin delete
    res_delete = client.delete(
        f"/api/v1/hero-products/{item_id}",
        headers={"Authorization": f"Bearer {adm_token}"}
    )
    assert res_delete.status_code == 200, f"Delete failed: {res_delete.text}"
    assert res_delete.json()["success"] is True
    print(f"[PASS] Admin deleted hero product successfully")

    print("\nALL HERO PRODUCT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_hero_products_crud()
