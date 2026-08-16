"""Renders a PersonalizationResult into the system + user messages sent to
the LLM. The only place that formats prompt text - the engine never
hardcodes prompt strings, and the LLM gateway never sees anything but
finished messages."""

from src.config.business_config import PersonalizationConfig
from src.config.prompt_registry import PromptRegistry
from src.models.internal_models import PersonalizationResult


class PromptBuilder:
    def __init__(self, prompts: PromptRegistry, config: PersonalizationConfig):
        self._prompts = prompts
        self._config = config

    def build_messages(self, result: PersonalizationResult, question: str) -> list[dict]:
        system_prompt = self._prompts.system_prompt_for(result.intent).format(
            language=result.language, tone=result.tone, max_words=result.max_words
        )

        degraded_instruction = ""
        if result.failed_services:
            available = ", ".join(self._config.label_for(p) for p in result.selected_context) or "none"
            degraded_instruction = self._prompts.instructions["degraded_context_notice"].format(
                missing_services=", ".join(result.failed_services),
                available_sources=available,
            )

        follow_up_instruction = self._prompts.instructions["follow_up"] if result.show_follow_up else ""

        user_prompt = self._prompts.user_prompts["default"].format(
            question=question,
            context=self._render_context(result.selected_context),
            degraded_instruction=degraded_instruction,
            follow_up_instruction=follow_up_instruction,
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _render_context(self, selected_context: dict[str, object]) -> str:
        if not selected_context:
            return "No astrological context is currently available."
        lines = [f"- {self._config.label_for(path)}: {value}" for path, value in selected_context.items()]
        return "\n".join(lines)
