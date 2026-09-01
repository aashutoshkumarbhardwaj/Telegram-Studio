from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ContentType(str, Enum):
    AI_NEWS = "ai_news"
    JOB = "job"
    INTERNSHIP = "internship"
    HACKATHON = "hackathon"
    AI_TOOL = "ai_tool"
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


class InlineButton(BaseModel):
    text: str
    url: str


class MediaItem(BaseModel):
    type: str = Field(..., description="photo, video, document, animation")
    url_or_path: str
    file_id: Optional[str] = None


class VerificationInfo(BaseModel):
    status: VerificationStatus = VerificationStatus.VERIFIED
    sources: List[str] = Field(default_factory=list)


class PostSchema(BaseModel):
    content_type: ContentType
    title: str
    body: str
    parse_mode: ParseMode = ParseMode.HTML
    source: Optional[Union[str, SourceInfo]] = None
    media: List[MediaItem] = Field(default_factory=list)
    buttons: List[InlineButton] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
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
