from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_serializer,
    field_validator,
    model_validator,
)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AdminRead(BaseModel):
    id: int
    email: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AdminRead


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: CategoryRead
    farmer_name: str
    description: str
    price: Decimal
    available_quantity: int
    image_url: str

    @field_serializer("price")
    def serialize_price(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ProductPage(BaseModel):
    items: list[ProductRead]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class AdminProductRead(ProductRead):
    status: Literal["active", "inactive"]
    version: int


class AdminProductPage(BaseModel):
    items: list[AdminProductRead]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    category_id: int = Field(ge=1)
    farmer_name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=3000)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    available_quantity: int = Field(ge=0, le=1_000_000)
    image_url: HttpUrl = Field(max_length=2048)
    status: Literal["active", "inactive"]

    @field_validator("name", "farmer_name", "description", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=160)
    category_id: int | None = Field(default=None, ge=1)
    farmer_name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, min_length=10, max_length=3000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    image_url: HttpUrl | None = Field(default=None, max_length=2048)

    @field_validator("name", "farmer_name", "description", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_empty_update(self):
        changes = self.model_dump(exclude_unset=True)
        if not changes:
            raise ValueError("At least one field must be supplied")
        if any(value is None for value in changes.values()):
            raise ValueError("Updated fields cannot be null")
        return self


class ProductStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "inactive"]


class ProductStockUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available_quantity: int = Field(ge=0, le=1_000_000)
    expected_version: int = Field(ge=1)
