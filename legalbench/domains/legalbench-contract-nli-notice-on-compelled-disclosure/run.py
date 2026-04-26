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
    ("clause_addresses_compelled_disclosure",
     "true if the clause addresses scenarios where the Receiving Party is compelled to disclose Confidential Information by law, regulation, or judicial process; false otherwise."),
    ("clause_requires_notification",
     "true if the clause imposes a notification or notice duty in such scenarios; false otherwise."),
    ("notification_duty_receiving_to_disclosing",
     "true if the duty to notify is assigned to the Receiving Party (the party compelled to disclose), with the notice running to the Disclosing Party; false if assigned otherwise or not at all."),
]

if __name__ == "__main__":
    sys.exit(run(here=HERE, task="contract_nli_notice_on_compelled_disclosure", fields=FIELDS))
