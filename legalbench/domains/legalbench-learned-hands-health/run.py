#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "requests>=2.28", "anthropic>=0.40"]
# ///
import sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "_lib"))
from single_clause_runner import run

FIELDS = [
    ("post_discusses_health_issue",
     "true if the post discusses any of: accessing health services, paying for medical care, getting public benefits for health care, protecting one's rights in medical settings, or other health-related issues; false otherwise."),
]

if __name__ == "__main__":
    sys.exit(run(here=HERE, task="learned_hands_health", fields=FIELDS))
