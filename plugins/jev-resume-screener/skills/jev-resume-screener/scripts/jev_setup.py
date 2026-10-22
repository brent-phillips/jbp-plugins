#!/usr/bin/env python3
"""Set up and verify the TypeSafe Jev connection.

  run.sh jev_setup.py --check   report where the key is and make one tiny test call
  run.sh jev_setup.py --save    prompt for the key (hidden input) and save it to
                                ~/.typesafe/api_key with owner-only permissions

The key never appears in the terminal, in logs, or in any file but the one above.
"""
import argparse
import getpass
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jev_client import JevClient, load_api_key  # noqa: E402

KEY_FILE = Path.home() / ".typesafe" / "api_key"


def where() -> str:
    if os.environ.get("TYPESAFE_API_KEY"):
        return "the TYPESAFE_API_KEY environment variable"
    if KEY_FILE.exists():
        return str(KEY_FILE)
    return ""


def test_call() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            jev = JevClient(Path(tmp), workers=1, timeout=30)
            res = jev.ask({"note": "connection test"},
                          {"ok": {"type": "noul", "instructions": "Is this a connection test?"}})
            p = res["answers"]["ok"]["noul"]
            return True, f"Jev answered (p={p:.2f})"
        except SystemExit as e:
            return False, str(e)
        except Exception as e:  # network, auth, quota
            return False, str(e)[:300]


def save() -> None:
    key = getpass.getpass("Paste your TypeSafe API key (input hidden): ").strip()
    if not key:
        sys.exit("No key entered; nothing saved.")
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(KEY_FILE.parent, 0o700)
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key + "\n")
    print(f"Saved to {KEY_FILE} (readable only by you).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--save", action="store_true")
    a = ap.parse_args()
    if a.save:
        save()
    src = where()
    if not src or not load_api_key():
        print("JEV_STATUS=missing_key")
        print(f"No TypeSafe API key found. Run:  {Path(__file__).parent / 'run.sh'} jev_setup.py --save")
        sys.exit(1)
    ok, msg = test_call()
    print(f"JEV_STATUS={'ok' if ok else 'error'}")
    print(f"Key found in {src}. {msg}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
