from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from core.keyword_config import keyword_config

router = APIRouter()


class MappingIn(BaseModel):
    keywords: list[str]
    url: str

    @field_validator("keywords")
    @classmethod
    def at_least_one_keyword(cls, v: list[str]) -> list[str]:
        if not any(k.strip() for k in v):
            raise ValueError("At least one non-empty keyword is required")
        return v

    @field_validator("url")
    @classmethod
    def non_empty_url(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("URL cannot be empty")
        return v


class MappingOut(BaseModel):
    id: str
    keywords: list[str]
    url: str
    created_at: str


@router.get("/config/mappings", response_model=list[MappingOut])
async def list_mappings():
    return await keyword_config.get_all()


@router.post("/config/mappings", response_model=MappingOut, status_code=201)
async def create_mapping(body: MappingIn):
    return await keyword_config.add(body.keywords, body.url)


@router.put("/config/mappings/{id}", response_model=MappingOut)
async def update_mapping(id: str, body: MappingIn):
    result = await keyword_config.update(id, body.keywords, body.url)
    if result is None:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return result


@router.delete("/config/mappings/{id}", status_code=204)
async def delete_mapping(id: str):
    deleted = await keyword_config.delete(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mapping not found")
