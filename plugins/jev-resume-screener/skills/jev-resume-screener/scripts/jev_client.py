"""Minimal client for TypeSafe's Jev (POST /v1/systemone).

Request:  {"model", "state", "questions": {name: {type, instructions, criteria}}}
Response: {"answers": {name: {type, noul | choice+confidence+probabilities |
           score+confidence+legend+probabilities}}, "usage": {...}}

Reference: https://docs.typesafe.ai/api

Features
- API key from TYPESAFE_API_KEY or ~/.typesafe/api_key
- Disk cache keyed on (model, state, questions): reruns during calibration
  only pay for requests that actually changed.
- Retries with backoff on 429 / 5xx, including 529 (overloaded).
- --mock mode: a crude offline stand-in so the pipeline can be tested with
  no key and no network. Mock answers are NOT Jev and must never be used
  to judge real candidates.
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import sha

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
STATE_CHAR_LIMIT = 90_000  # state is capped at ~32k tokens; stay well under


def load_api_key() -> str | None:
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        return key.strip()
    f = Path.home() / ".typesafe" / "api_key"
    return f.read_text().strip() if f.exists() else None


class JevClient:
    def __init__(self, cache_dir: Path, model: str = DEFAULT_MODEL, mock: bool = False,
                 workers: int = 8, timeout: int = 60):
        self.model = model
        self.mock = mock
        self.workers = workers
        self.timeout = timeout
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.usage = {"requests": 0, "cached": 0, "input_tokens": 0}
        self.key = None if mock else load_api_key()
        if not mock and not self.key:
            raise SystemExit(
                "No TypeSafe API key found. Set TYPESAFE_API_KEY or save it to "
                "~/.typesafe/api_key, or run with --mock to test offline."
            )

    # ----- public -----

    def ask(self, state, questions: dict) -> dict:
        """One request: a shared state and a dict of named questions."""
        if isinstance(state, dict):
            state = {k: (v[:STATE_CHAR_LIMIT] if isinstance(v, str) else v) for k, v in state.items()}
        payload = {"model": self.model, "state": state, "questions": questions}
        key = sha(json.dumps(payload, sort_keys=True) + ("|mock" if self.mock else ""))
        cached = self.cache_dir / f"{key}.json"
        if cached.exists():
            self.usage["cached"] += 1
            return json.loads(cached.read_text())
        result = self._mock(state, questions) if self.mock else self._post(payload)
        # write-then-rename: identical resumes send identical requests in parallel threads,
        # and a reader must never see a half-written cache file
        tmp = cached.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(result))
        tmp.replace(cached)
        self.usage["requests"] += 1
        self.usage["input_tokens"] += result.get("usage", {}).get("input_tokens", 0)
        return result

    def ask_many(self, jobs: list[tuple]) -> list[dict]:
        """jobs: [(state, questions), ...] run in parallel, results in order."""
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return list(pool.map(lambda j: self.ask(*j), jobs))

    # ----- network -----

    def _post(self, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(5):
            req = urllib.request.Request(
                ENDPOINT, data=body, method="POST",
                headers={"Authorization": f"Bearer {self.key}",
                         "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")[:500]
                if e.code in (429, 500, 502, 503, 504, 529) and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Jev HTTP {e.code}: {detail}") from e
            except urllib.error.URLError as e:
                if attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Jev network error: {e}") from e
        raise RuntimeError("Jev request failed after retries")

    # ----- offline mock (keyword overlap; for plumbing tests only) -----

    @staticmethod
    def _words(x) -> set[str]:
        text = json.dumps(x) if not isinstance(x, str) else x
        return {w for w in re.findall(r"[a-z][a-z0-9+#]{3,}", text.lower())}

    def _mock(self, state, questions: dict) -> dict:
        if isinstance(state, dict) and "resume" in state:
            text = state["resume"]
        elif isinstance(state, dict) and "resume_a" in state:
            a, b = self._words(state["resume_a"]), self._words(state["resume_b"])
            sim = len(a & b) / max(1, len(a | b))
            p = round(min(0.99, sim * 1.1), 2)
            answers = {}
            for name, q in questions.items():
                if q["type"] == "score":
                    top = len(q["criteria"]) - 1
                    answers[name] = {"type": "score", "score": round(p * top, 2),
                                     "confidence": round(0.5 + abs(p - 0.5), 2),
                                     "legend": {str(i): c for i, c in enumerate(q["criteria"])},
                                     "probabilities": {}}
                else:
                    answers[name] = {"type": "noul", "noul": p}
            return {"model": "mock", "usage": {"input_tokens": 0}, "answers": answers}
        else:
            text = state if isinstance(state, str) else json.dumps(state)
        have = self._words(text)
        answers = {}
        for name, q in questions.items():
            want = self._words(q.get("instructions", "")) | self._words(q.get("criteria", ""))
            want -= {"does", "resume", "candidate", "show", "have", "with", "least", "years",
                     "much", "experience", "this", "that", "from", "into", "their", "they"}
            hit = len(want & have) / max(1, len(want))
            if name == "jd_mirror" and isinstance(state, dict):
                jd = self._words(state.get("job_description", ""))
                hit = len(jd & have) / max(1, len(jd))
            p = round(min(0.97, max(0.03, 0.1 + hit * 1.4)), 2)
            if q["type"] == "noul":
                answers[name] = {"type": "noul", "noul": p}
            elif q["type"] == "score":
                n = len(q["criteria"])
                score = round(p * (n - 1), 2)
                answers[name] = {"type": "score", "score": score,
                                 "confidence": round(0.5 + abs(p - 0.5), 2),
                                 "legend": {str(i): c for i, c in enumerate(q["criteria"])},
                                 "probabilities": {}}
            else:
                first = next(iter(q["criteria"]))
                answers[name] = {"type": "choice", "choice": first, "confidence": 0.5,
                                 "probabilities": {}}
        return {"model": "mock", "usage": {"input_tokens": 0}, "answers": answers}
