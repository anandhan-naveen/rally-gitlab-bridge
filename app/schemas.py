from pydantic import BaseModel, Field
from typing import Literal

class ImportRequest(BaseModel):
    scope_type: Literal['quarter', 'feature', 'story']
    scope_value: str
    include_tasks: bool = True
    squad_only: bool = True
    dry_run: bool = True

class SyncRequest(BaseModel):
    direction: Literal['reconcile', 'rally_to_gitlab', 'gitlab_to_rally'] = 'reconcile'
    scope_type: Literal['all', 'quarter', 'feature', 'story'] = 'all'
    scope_value: str | None = None
    dry_run: bool = False

class ImportPlan(BaseModel):
    scope: str
    stories_found: int
    squad_stories: int
    tasks_found: int
    already_linked: int
    to_create: int
    excluded: int
    items: list[dict] = Field(default_factory=list)
