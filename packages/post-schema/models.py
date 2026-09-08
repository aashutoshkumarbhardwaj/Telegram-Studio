from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ContentType(str, Enum):
    AI_NEWS = "ai_news"
    JOB = "job"
    INTERNSHIP = "internship"
    HACKATHON = "hackathon"
    AI_TOOL = "ai_tool"
    GITHUB = "github"
    CAREER = "career"
    RESOURCE = "resource"


class ParseMode(str, Enum):
    HTML = "HTML"
    MARKDOWN_V2 = "MarkdownV2"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    NEEDS_VERIFICATION = "needs_verification"
    UNVERIFIED = "unverified"


class SourceInfo(BaseModel):
    title: Optional[str] = None
    url: str
    author: Optional[str] = None
    published_at: Optional[str] = None


class InlineButton(BaseModel):
    text: str
    url: Optional[str] = None
    callback_data: Optional[str] = None
    row: Optional[int] = None


class MediaItem(BaseModel):
    type: str = Field(..., description="photo, video, document, animation")
    url_or_path: str
    caption: Optional[str] = None
    file_id: Optional[str] = None


class VerificationInfo(BaseModel):
    status: VerificationStatus = VerificationStatus.VERIFIED
    sources: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None


class PostSchema(BaseModel):
    content_type: ContentType
    title: str
    body: str
    parse_mode: ParseMode = ParseMode.HTML
    schema_version: Optional[str] = None
    summary: Optional[str] = None
    takeaways: List[str] = Field(default_factory=list)
    why_it_matters: Optional[str] = None
    cta: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[Union[str, SourceInfo]] = None
    media: List[MediaItem] = Field(default_factory=list)
    buttons: List[InlineButton] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    reactions: List[str] = Field(default_factory=list)
    image_prompt: Optional[str] = None
    verification: VerificationInfo = Field(default_factory=VerificationInfo)

    @field_validator("source", mode="before")
    @classmethod
    def parse_source(cls, v):
        if isinstance(v, str):
            return v.strip()
        if isinstance(v, dict):
            return SourceInfo(**v)
        return v

    def get_source_url(self) -> Optional[str]:
        if not self.source:
            return None
        if isinstance(self.source, str):
            return self.source
        return self.source.url

    def get_source_title(self) -> Optional[str]:
        if not self.source:
            return None
        if isinstance(self.source, str):
            return self.source
        return self.source.title or self.source.url

