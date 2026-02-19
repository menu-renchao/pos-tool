from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine, Base, AsyncSessionLocal
from app.models import User, ScanSession
from app.core.security import get_password_hash


async def cleanup_old_results(db: AsyncSession):
    """Clean up scan results older than 24 hours."""
    from app.models import ScanResult

    threshold = datetime.now() - timedelta(hours=24)
    result = await db.execute(
        select(ScanResult).where(ScanResult.scanned_at < threshold)
    )
    old_results = result.scalars().all()
    for r in old_results:
        await db.delete(r)
    if old_results:
        print(f"Cleaned up {len(old_results)} old scan results")


async def init_db():
    """Initialize database and create default admin."""
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(User).where(User.username == "admin"))
            admin = result.scalar_one_or_none()

            if not admin:
                admin = User(
                    username="admin",
                    email="admin@example.com",
                    role="admin",
                    status="approved",
                    password_hash=get_password_hash("admin123"),
                )
                db.add(admin)
                await db.commit()
                print("Created default admin user")

            # Initialize scan session
            result = await db.execute(select(ScanSession).where(ScanSession.id == 1))
            session = result.scalar_one_or_none()
            if not session:
                session = ScanSession(id=1)
                db.add(session)
                await db.commit()
                print("Initialized scan session")

            # Cleanup old results
            await cleanup_old_results(db)

        except Exception as e:
            await db.rollback()
            print(f"Error initializing database: {e}")
            raise
