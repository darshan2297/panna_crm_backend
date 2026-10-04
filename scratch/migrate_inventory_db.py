import sys
sys.path.append(".")
import sqlite3
from app.core.database import engine, Base
import app.models  # load all models

Base.metadata.create_all(bind=engine)
print("Base.metadata.create_all completed!")

# Also run seeding so extra items and transactions are populated
from app.core.database import SessionLocal
from app.services.seed_service import seed_dashboard_data

db = SessionLocal()
seed_dashboard_data(db)
db.close()
print("Seeding completed successfully!")
