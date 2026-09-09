from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


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
