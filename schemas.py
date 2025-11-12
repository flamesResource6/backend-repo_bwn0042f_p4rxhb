"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

# Core domain schemas for this project

class Family(BaseModel):
    name: str
    parent_email: EmailStr

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    role: Literal["parent", "child"] = Field(..., description="Role of the user")
    name: str = Field(..., description="Full name")
    email: Optional[EmailStr] = Field(None, description="Email address (optional for children)")
    age: Optional[int] = Field(None, ge=3, le=120, description="Age in years")
    family_id: Optional[str] = Field(None, description="Family grouping identifier")
    is_active: bool = Field(True, description="Whether user is active")

class Message(BaseModel):
    child_id: str = Field(..., description="ID of the child user")
    text: str = Field(..., description="Message content from child")
    emotion: Optional[str] = Field(None, description="Detected emotion label")
    risk_score: Optional[float] = Field(None, ge=0, le=1, description="Risk score 0-1")
    response: Optional[str] = Field(None, description="Assistant reply")

class RiskEvent(BaseModel):
    child_id: str
    level: Literal["low", "medium", "high"]
    reason: str
    score: float = Field(..., ge=0, le=1)
    occurred_at: Optional[datetime] = None

class Schedule(BaseModel):
    child_id: str
    label: str = Field(..., description="e.g., Study, Bedtime")
    start_minute: int = Field(..., ge=0, le=1440)
    end_minute: int = Field(..., ge=0, le=1440)
    days: List[int] = Field(default_factory=list, description="0=Mon ... 6=Sun")

# Example retained for reference
class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
