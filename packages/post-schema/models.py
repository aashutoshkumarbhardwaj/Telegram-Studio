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
    url: Optional[str] = ""
    author: Optional[str] = None
    published_at: Optional[str] = None


class InlineButton(BaseModel):
    text: str = ""
    url: Optional[str] = None
    callback_data: Optional[str] = None
    row: Optional[int] = None


class MediaItem(BaseModel):
    type: str = Field(default="photo", description="photo, video, document, animation")
    url_or_path: str = ""
    caption: Optional[str] = None
    file_id: Optional[str] = None


class VerificationInfo(BaseModel):
    status: VerificationStatus = VerificationStatus.VERIFIED
    sources: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, v):
        if isinstance(v, str):
            v_clean = v.lower().strip()
            for s in VerificationStatus:
                if s.value == v_clean or s.name.lower() == v_clean:
                    return s
        return v or VerificationStatus.VERIFIED


class PostSchema(BaseModel):
    content_type: ContentType
    title: str
    body: str
    parse_mode: ParseMode = ParseMode.HTML
    schema_version: Optional[str] = "1.0.0"
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

    @field_validator("content_type", mode="before")
    @classmethod
    def parse_content_type(cls, v):
        if isinstance(v, str):
            v_clean = v.lower().strip()
            for ct in ContentType:
                if ct.value == v_clean or ct.name.lower() == v_clean:
                    return ct
            if v_clean in ("auto", "general", "news", "update"):
                return ContentType.AI_NEWS
            if v_clean in ("jobs", "hiring", "role"):
                return ContentType.JOB
            if v_clean in ("internships", "fellowship"):
                return ContentType.INTERNSHIP
            if v_clean in ("hackathons", "competition"):
                return ContentType.HACKATHON
            if v_clean in ("tool", "tools"):
                return ContentType.AI_TOOL
            if v_clean in ("repo", "repository", "git"):
                return ContentType.GITHUB
            if v_clean in ("careers", "guide", "tips"):
                return ContentType.CAREER
            if v_clean in ("resources", "cheatsheet", "docs"):
                return ContentType.RESOURCE
        return v or ContentType.AI_NEWS

    @field_validator("parse_mode", mode="before")
    @classmethod
    def parse_parse_mode(cls, v):
        if isinstance(v, str):
            v_upper = v.upper().strip()
            if "HTML" in v_upper:
                return ParseMode.HTML
            if "MARKDOWN" in v_upper:
                return ParseMode.MARKDOWN_V2
        return v or ParseMode.HTML

    @field_validator("source", mode="before")
    @classmethod
    def parse_source(cls, v):
        if not v:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        if isinstance(v, dict):
            # Check if all fields are empty/None
            if not any(v.values()):
                return None
            valid_keys = {k: v[k] for k in v if k in SourceInfo.model_fields}
            return SourceInfo(**valid_keys)
        return v

    @field_validator("title", mode="before")
    @classmethod
    def parse_title(cls, v):
        if v is None:
            return ""
        return str(v)

    @field_validator("body", mode="before")
    @classmethod
    def parse_body(cls, v):
        if v is None:
            return ""
        return str(v)

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


