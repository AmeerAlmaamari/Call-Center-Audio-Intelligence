"""
Seed script to populate the database with sample agents and products.
Run with: python -m backend.app.db.seed
"""
import asyncio
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from .database import AsyncSessionLocal
from .models import Agent, Product


SAMPLE_AGENTS = [
    {"name": "Alice Johnson", "email": "alice.johnson@company.com", "department": "Sales"},
    {"name": "Bob Smith", "email": "bob.smith@company.com", "department": "Sales"},
    {"name": "Carol Williams", "email": "carol.williams@company.com", "department": "Support"},
    {"name": "David Brown", "email": "david.brown@company.com", "department": "Sales"},
    {"name": "Eva Martinez", "email": "eva.martinez@company.com", "department": "Support"},
]

SAMPLE_PRODUCTS = [
    {"name": "Basic Plan", "description": "Entry-level subscription with core features", "category": "Subscription"},
    {"name": "Pro Plan", "description": "Professional subscription with advanced features", "category": "Subscription"},
    {"name": "Enterprise Plan", "description": "Full-featured enterprise solution", "category": "Subscription"},
    {"name": "Add-on: Analytics", "description": "Advanced analytics and reporting module", "category": "Add-on"},
    {"name": "Add-on: Support Plus", "description": "Priority support with dedicated account manager", "category": "Add-on"},
    {"name": "Training Package", "description": "Onboarding and training sessions", "category": "Service"},
    {"name": "Consulting Hours", "description": "Expert consulting services", "category": "Service"},
]


async def seed_agents(session: AsyncSession) -> None:
    for agent_data in SAMPLE_AGENTS:
        agent = Agent(
            id=uuid.uuid4(),
            name=agent_data["name"],
            email=agent_data["email"],
            department=agent_data["department"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(agent)
    await session.commit()
    print(f"Seeded {len(SAMPLE_AGENTS)} agents.")


async def seed_products(session: AsyncSession) -> None:
    for product_data in SAMPLE_PRODUCTS:
        product = Product(
            id=uuid.uuid4(),
            name=product_data["name"],
            description=product_data["description"],
            category=product_data["category"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(product)
    await session.commit()
    print(f"Seeded {len(SAMPLE_PRODUCTS)} products.")


async def run_seed() -> None:
    async with AsyncSessionLocal() as session:
        await seed_agents(session)
        await seed_products(session)
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(run_seed())
