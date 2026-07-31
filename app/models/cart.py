from beanie import Document, PydanticObjectId

class CartItem(Document):
    session_id: str
    product_id: PydanticObjectId
    quantity: int = 1

    class Settings:
        name = "cart_items"
