from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app import models, schemas, crud

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if we already have categories
    if db.query(models.Category).first():
        print("Database already seeded.")
        return

    # Seed Categories
    cat_chandeliers = crud.create_category(db, schemas.CategoryCreate(name="Chandeliers"))
    cat_pendant = crud.create_category(db, schemas.CategoryCreate(name="Pendant Lights"))

    # Seed Products
    crud.create_product(db, schemas.ProductCreate(
        title="AURORA CHANDELIER",
        price=800.0,
        description="Exceptional quality classic lamp.",
        category_id=cat_chandeliers.id,
        stock_count=8,
        rating=5.0,
        review_count=14,
        is_featured=True,
        is_new_arrival=True,
        image_url="/images/lamp_classic_1784107722127.jpg"
    ))

    # Seed Projects
    crud.create_project(db, schemas.ProjectCreate(
        title="Lounge Project",
        installations_count="100+ Installed",
        image_url="/images/project_lounge_1784107767735.jpg",
        is_featured=True
    ))

    # Seed Testimonials
    crud.create_testimonial(db, schemas.TestimonialCreate(
        author_name="Anna Clark",
        author_title="Interior Designer",
        text="The quality and craftsmanship are truly exceptional.",
        rating=5.0
    ))

    print("Successfully seeded database!")
    db.close()

if __name__ == "__main__":
    seed()
