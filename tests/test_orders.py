import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.core.database import db
from bson import ObjectId

@pytest.mark.anyio
async def test_orders_api_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a test order
        order_payload = {
            "email": "customer@deluzex.com",
            "phone": "+919876543210",
            "shipping_address": {
                "first_name": "Test",
                "last_name": "User",
                "street": "123 Modern Street",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pin_code": "400001"
            },
            "items": [
                {
                    "product_id": "prod_123",
                    "title": "Pendant Lights",
                    "price": 1499.0,
                    "quantity": 2,
                    "image": "https://ik.imagekit.io/2s78gfu2x/categories/pendentlight.jpeg"
                }
            ],
            "subtotal": 2998.0,
            "gst": 539.64,
            "delivery": 0.0,
            "total": 3537.64,
            "payment_method": "cod",
            "notes": "Handle with care"
        }

        create_res = await ac.post("/api/v1/orders", json=order_payload)
        assert create_res.status_code == 201, create_res.text
        order_data = create_res.json()
        assert "_id" in order_data or "id" in order_data
        order_id = order_data.get("_id") or order_data.get("id")
        assert order_data["email"] == "customer@deluzex.com"
        assert order_data["total"] == 3537.64
        assert len(order_data["items"]) == 1
        assert order_data["items"][0]["title"] == "Pendant Lights"
        assert order_data["items"][0]["price"] == 1499.0
        assert order_data["items"][0]["quantity"] == 2

        # 2. Get Order by ID
        get_res = await ac.get(f"/api/v1/orders/{order_id}")
        assert get_res.status_code == 200
        fetched_order = get_res.json()
        assert (fetched_order.get("_id") or fetched_order.get("id")) == order_id
        assert fetched_order["status"] == "cod"

        # 3. Filter orders by email
        list_res = await ac.get("/api/v1/orders?email=customer@deluzex.com")
        assert list_res.status_code == 200
        orders_list = list_res.json()
        assert isinstance(orders_list, list)
        assert any((o.get("_id") or o.get("id")) == order_id for o in orders_list)

        # 4. Update Order Status
        status_res = await ac.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "processing", "tracking_number": "TRK-987654", "notes": "Packaging order"}
        )
        assert status_res.status_code == 200
        updated_order = status_res.json()
        assert updated_order["status"] == "processing"
        assert updated_order["tracking_number"] == "TRK-987654"

        # 5. Cancel Order
        cancel_res = await ac.post(f"/api/v1/orders/{order_id}/cancel")
        assert cancel_res.status_code == 200
        cancel_data = cancel_res.json()
        assert cancel_data["success"] is True
        assert cancel_data["status"] == "cancelled"

        # 6. Verify cancelled status
        final_get = await ac.get(f"/api/v1/orders/{order_id}")
        assert final_get.status_code == 200
        assert final_get.json()["status"] == "cancelled"

        # Cleanup test document from database
        try:
            db.orders.delete_one({"_id": ObjectId(order_id)})
        except Exception:
            pass
