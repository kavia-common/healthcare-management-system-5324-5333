from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom type for Pydantic to handle MongoDB ObjectId."""

    @classmethod
    def __get_pydantic_core_schema__(cls, _source, _handler):
        from pydantic_core import core_schema

        def validate_from_str(v: Any) -> ObjectId:
            if isinstance(v, ObjectId):
                return v
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid ObjectId")
            return ObjectId(v)

        return core_schema.no_info_after_validator_function(
            validate_from_str,
            core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.str_schema(),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda v: str(v), when_used="json-unless-none"
            ),
        )


class MongoModel(BaseModel):
    """Base model providing id mapping between _id and id for MongoDB documents."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="ignore",
    )
