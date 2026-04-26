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
    ("clause_awards_liquidated_damages",
     "true if the clause awards a pre-specified amount payable on breach (in lieu of or supplementing actual damages); false otherwise."),
    ("clause_awards_termination_fee",
     "true if the clause awards a fee upon termination of the contract; false otherwise."),
]

if __name__ == "__main__":
    sys.exit(run(here=HERE, task="cuad_liquidated_damages", fields=FIELDS))
