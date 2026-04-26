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
    ("clause_targets_specific_user_group",
     "true if the clause's scope targets a specifically-identified subgroup of users (e.g. children, residents of a particular jurisdiction such as California or the EU, members of a particular service tier, employees, or analogous specific group); false if it applies to all users with no group-specific scoping."),
]

if __name__ == "__main__":
    sys.exit(run(here=HERE, task="opp115_international_and_specific_audiences", fields=FIELDS))
