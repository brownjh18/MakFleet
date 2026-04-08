"""
MakFleet Prototype - Data Seeder
Script to seed initial drivers and vehicles into the database
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal
from backend.models import Driver, Vehicle


def seed_drivers_and_vehicles():
    """Seed initial drivers and vehicles"""
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_drivers = db.query(Driver).count()
        if existing_drivers > 0:
            print(f"Database already has {existing_drivers} drivers. Skipping seed.")
            return
        
        # Create drivers
        drivers_data = [
            {"name": "John Kato", "phone": "+256772123456", "license_number": "DL001234"},
            {"name": "David Ssali", "phone": "+256772234567", "license_number": "DL002345"},
            {"name": "Michael Oceng", "phone": "+256772345678", "license_number": "DL003456"},
            {"name": "Robert Mukama", "phone": "+256772456789", "license_number": "DL004567"},
            {"name": "Francis Buwembo", "phone": "+256772567890", "license_number": "DL005678"},
        ]
        
        drivers = []
        for d in drivers_data:
            driver = Driver(
                name=d["name"],
                phone=d["phone"],
                license_number=d["license_number"]
            )
            db.add(driver)
            drivers.append(driver)
        
        db.commit()
        
        # Refresh to get IDs
        for driver in drivers:
            db.refresh(driver)
        
        print(f"Created {len(drivers)} drivers")
        
        # Create vehicles
        vehicles_data = [
            {"plate_number": "UGA 001M", "model": "Honda Dio", "driver_id": drivers[0].driver_id},
            {"plate_number": "UGA 002M", "model": "TVS King", "driver_id": drivers[1].driver_id},
            {"plate_number": "UGA 003M", "model": "Bajaj Boxer", "driver_id": drivers[2].driver_id},
            {"plate_number": "UGA 004M", "model": "Honda Activa", "driver_id": drivers[3].driver_id},
            {"plate_number": "UGA 005M", "model": "TVS NTORQ", "driver_id": drivers[4].driver_id},
        ]
        
        for v in vehicles_data:
            vehicle = Vehicle(
                plate_number=v["plate_number"],
                model=v["model"],
                driver_id=v["driver_id"],
                status="active"
            )
            db.add(vehicle)
        
        db.commit()
        
        print(f"Created {len(vehicles_data)} vehicles")
        print("\nSeeding completed successfully!")
        print("\nDrivers:")
        for d in drivers:
            print(f"  - ID: {d.driver_id}, Name: {d.name}, License: {d.license_number}")
        print("\nVehicles:")
        for v in vehicles_data:
            print(f"  - Plate: {v['plate_number']}, Model: {v['model']}, Driver ID: {v['driver_id']}")
            
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting MakFleet data seeding...")
    print("-" * 50)
    
    # Initialize database first
    from backend.database import init_db
    init_db()
    
    seed_drivers_and_vehicles()
