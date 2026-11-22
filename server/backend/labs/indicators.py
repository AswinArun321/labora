"""
Neutral review indicators for teachers (slides 9-10 of the project deck).

These are hints that something is worth a closer look in the history. They are
NOT proof of copying and LABORA makes no claim to detect AI-written code.
"""
from datetime import timedelta

from django.conf import settings

from .models import ActivityEvent, Submission


def _changed_ratio(old: str, new: str) -> float:
    import difflib

    if not new:
        return 0.0
    sm = difflib.SequenceMatcher(None, old or "", new)
    return 1 - sm.ratio()


def compute_indicators(sub: Submission) -> list[dict]:
    out = []
    events = list(sub.events.all())

    # batched typing totals are excluded: only single insertions count here
    big = [e for e in events if e.kind == ActivityEvent.Kind.INSERT and not e.detail.get("batch")
           and e.chars >= settings.INDICATOR_LARGE_INSERT_CHARS]
    if big:
        out.append({
            "code": "large_insertion",
            "label": "Large insertion",
            "detail": f"{len(big)} single insertion(s) of {settings.INDICATOR_LARGE_INSERT_CHARS}+ characters "
                      f"(largest {max(e.chars for e in big)}).",
        })

    blocked = sum(1 for e in events if e.kind in (ActivityEvent.Kind.PASTE_BLOCKED, ActivityEvent.Kind.DROP_BLOCKED))
    if blocked:
        out.append({"code": "blocked_paste", "label": "Blocked paste attempts",
                    "detail": f"{blocked} attempt(s) to paste or drop content from outside LABORA."})

    left = sum(1 for e in events if e.kind in (ActivityEvent.Kind.FOCUS_LOST, ActivityEvent.Kind.FULLSCREEN_EXIT))
    if left:
        out.append({"code": "left_window", "label": "Left the window",
                    "detail": f"Left the workspace / fullscreen {left} time(s)."})

    alerts = [e for e in events if e.kind == ActivityEvent.Kind.SECURE_ALERT]
    if alerts:
        out.append({"code": "secure_alert", "label": "Secure browser alerts",
                    "detail": "; ".join(sorted({str(e.detail.get('message', 'alert')) for e in alerts}))[:300]})

    if sub.practical.restricted and events and not any(e.secure_browser for e in events):
        out.append({"code": "normal_browser", "label": "Normal browser",
                    "detail": "Work was done outside the LABORA Secure Browser."})

    if sub.submitted_at:
        cutoff = sub.submitted_at - timedelta(minutes=settings.INDICATOR_LATE_CHANGE_MINUTES)
        before = sub.versions.filter(created_at__lte=cutoff).order_by("-number").first()
        if before is not None:
            ratio = _changed_ratio(before.code, sub.code)
            if ratio >= settings.INDICATOR_LATE_CHANGE_RATIO:
                out.append({"code": "late_changes", "label": "Late changes",
                            "detail": f"About {round(ratio * 100)}% of the program changed in the last "
                                      f"{settings.INDICATOR_LATE_CHANGE_MINUTES} minutes before submission."})
    return out
