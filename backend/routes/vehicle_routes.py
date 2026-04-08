"""
MakFleet Prototype - Vehicle Routes
API endpoints for vehicle and driver management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from ..database import get_db
from ..models import Vehicle, Driver


router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


# Pydantic schemas
class VehicleCreate(BaseModel):
    plate_number: str
    driver_id: int
    model: str
    status: str = "active"


class DriverCreate(BaseModel):
    name: str
    phone: str
    license_number: str


class VehicleResponse(BaseModel):
    vehicle_id: int
    plate_number: str
    driver_id: int
    model: str
    status: str

    class Config:
        from_attributes = True


class DriverResponse(BaseModel):
    driver_id: int
    name: str
    phone: str
    license_number: str

    class Config:
        from_attributes = True


@router.get("/")
def get_vehicles(
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all vehicles
    """
    query = db.query(Vehicle)
    if status:
        query = query.filter(Vehicle.status == status)
    vehicles = query.all()
    
    result = []
    for v in vehicles:
        driver = db.query(Driver).filter(Driver.driver_id == v.driver_id).first()
        result.append({
            "vehicle_id": v.vehicle_id,
            "plate_number": v.plate_number,
            "model": v.model,
            "status": v.status,
            "driver": {
                "driver_id": driver.driver_id,
                "name": driver.name,
                "phone": driver.phone
            } if driver else None
        })
    
    return result


@router.get("/{vehicle_id}")
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """Get a specific vehicle by ID"""
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    driver = None
    if vehicle.driver_id:
        driver = db.query(Driver).filter(Driver.driver_id == vehicle.driver_id).first()
    
    return {
        "vehicle_id": vehicle.vehicle_id,
        "plate_number": vehicle.plate_number,
        "model": vehicle.model,
        "status": vehicle.status,
        "driver": {
            "driver_id": driver.driver_id,
            "name": driver.name,
            "phone": driver.phone,
            "license_number": driver.license_number
        } if driver else None
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    """Create a new vehicle"""
    # Check if driver exists
    driver = db.query(Driver).filter(Driver.driver_id == vehicle.driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Check if plate number already exists
    existing = db.query(Vehicle).filter(Vehicle.plate_number == vehicle.plate_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plate number already exists"
        )
    
    new_vehicle = Vehicle(
        plate_number=vehicle.plate_number,
        driver_id=vehicle.driver_id,
        model=vehicle.model,
        status=vehicle.status
    )
    
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    
    return new_vehicle


# Driver routes
@router.get("/drivers/")
def get_drivers(db: Session = Depends(get_db)):
    """Get all drivers"""
    drivers = db.query(Driver).all()
    return drivers


@router.get("/drivers/{driver_id}")
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    """Get a specific driver"""
    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Get vehicles for this driver
    vehicles = db.query(Vehicle).filter(Vehicle.driver_id == driver_id).all()
    
    return {
        "driver_id": driver.driver_id,
        "name": driver.name,
        "phone": driver.phone,
        "license_number": driver.license_number,
        "vehicles": [
            {
                "vehicle_id": v.vehicle_id,
                "plate_number": v.plate_number,
                "model": v.model,
                "status": v.status
            }
            for v in vehicles
        ]
    }


@router.post("/drivers/", status_code=status.HTTP_201_CREATED)
def create_driver(driver: DriverCreate, db: Session = Depends(get_db)):
    """Create a new driver"""
    # Check if license number already exists
    existing = db.query(Driver).filter(Driver.license_number == driver.license_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License number already exists"
        )
    
    new_driver = Driver(
        name=driver.name,
        phone=driver.phone,
        license_number=driver.license_number
    )
    
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    
    return new_driver
