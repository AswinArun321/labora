"""
Optional, teacher-side AI summary (slide 9). Students never get AI help.

Only the program text and anonymous activity counts are sent - no names, roll
numbers or other personal details. The API key stays on the backend.
"""
import requests
from django.conf import settings


class AIUnavailable(Exception):
    pass


def ai_enabled() -> bool:
    return bool(settings.AI_API_KEY)


def summarize_submission(language: str, question: str, code: str, indicators: list[dict], versions: int) -> str:
    if not ai_enabled():
        raise AIUnavailable("AI review is not configured (set AI_API_KEY on the server).")
    ind = "; ".join(f"{i['label']}: {i['detail']}" for i in indicators) or "none"
    prompt = (
        "You help a college lab teacher review a student's practical. Do NOT judge whether code was written "
        "by AI and do not accuse the student. In under 180 words: (1) summarise the program structure, "
        "(2) list the programming concepts used, (3) say whether it appears to address the question, "
        "(4) point out anything in the activity indicators the teacher may want to look at in the history.\n\n"
        f"Language: {language}\nQuestion: {question}\nSaved versions: {versions}\nIndicators: {ind}\n\n"
        f"Program:\n```\n{code[:8000]}\n```"
    )
    try:
        resp = requests.post(
            settings.AI_BASE_URL.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
            json={"model": settings.AI_MODEL, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # network / provider errors are shown to the teacher as a message
        raise AIUnavailable(f"AI provider error: {exc}") from exc
