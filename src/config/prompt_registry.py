"""Tier 4 config: the PromptOps registry loaded from prompts.yaml."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel


class PromptRegistry(BaseModel):
    version: str
    system_prompts: dict[str, str]
    user_prompts: dict[str, str]
    instructions: dict[str, str]

    def system_prompt_for(self, intent: str) -> str:
        return self.system_prompts.get(intent, self.system_prompts["default"])


@lru_cache
def load_prompt_registry(path: str = "config/prompts.yaml") -> PromptRegistry:
    raw = yaml.safe_load(Path(path).read_text())
    return PromptRegistry(**raw)
