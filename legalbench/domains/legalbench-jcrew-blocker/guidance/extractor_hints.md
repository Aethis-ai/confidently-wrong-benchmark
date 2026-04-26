# Subject-matter-expert guidance for the J.Crew Blocker extractor

These are practitioner-level notes for the runtime LLM extractor that
reads each contract clause and decides whether each prong of the
J.Crew Blocker rule is satisfied. They are written in plain English,
do not reference any LegalBench case, label, or output from any model
run against this benchmark, and are derived from standard
leveraged-finance drafting practice (LSTA Model Credit Agreement
provisions, practitioner press on the 2016 J.Crew amendment, and
common credit-facility terminology used by major loan markets desks).

These hints are loaded by `run.py` into the extractor prompt alongside
the verbatim canonical rule from `sources/rule.md` and the SME hints
in `guidance/hints.yaml`. They do not change the rule itself — they
help the extractor recognise the rule's prongs when the actual
contract drafting uses synonymous or jurisdiction-specific terminology.

## Synonyms for "unrestricted subsidiary" in real loan documents

The canonical task description uses the term *unrestricted subsidiary*.
Real credit-facility drafting frequently uses one of these synonymous
or near-equivalent terms; recognise them all as the same concept for
the prohibition prong:

- "Unrestricted Subsidiary" (the canonical term)
- "non-Loan Party Subsidiary" — i.e. a subsidiary that is not party
  to the loan as a borrower or guarantor
- "non-Guarantor Subsidiary" — same idea, framed around the
  guarantor structure
- "non-Restricted Subsidiary" — i.e. any subsidiary that is not a
  Restricted Subsidiary (the negation of the standard restricted
  category)
- "Excluded Subsidiary"
- "subsidiary that is not a Restricted Subsidiary"
- references to subsidiaries that are "designated as Unrestricted"
  or "redesignated"

A clause that prohibits IP transfer to any of the above is a
prohibition on transfer to an unrestricted subsidiary for the purposes
of identifying a J.Crew Blocker.

## Common phrasings of the prohibition prong

The prohibition does not need to use the exact word "prohibits".
Recognise these as forms of the prohibition prong:

- "no Loan Party shall sell, transfer, assign, or dispose of … to any
  [non-Loan Party / unrestricted] Subsidiary"
- "the Borrower shall not transfer Material Intellectual Property to
  …"
- "no Material Intellectual Property … shall be transferred to …"
- "the Borrower is prohibited from designating … as an Unrestricted
  Subsidiary if such designation would cause Material Intellectual
  Property to be held by …"
- negative covenants restricting asset transfers framed around the
  Restricted Subsidiary group

## Carve-outs do not defeat the prohibition prong

It is common drafting practice to attach narrow exceptions to the
prohibition (e.g. *"unless such transfer is for a bona fide business
purpose"*, *"except as permitted by Section X"*, *"other than to a
wholly-owned Restricted Subsidiary"*). These carve-outs do not defeat
the J.Crew Blocker classification — the clause still contains the
prohibition; the carve-out is just a permitted exception. Recognise a
clause as containing the prohibition prong even if it is qualified by
narrow exceptions of this kind.

## Materiality scope

Many real J.Crew Blocker provisions restrict only "material
intellectual property" rather than "all intellectual property". This
narrower scope is consistent with the prohibition prong; the original
2016 J.Crew workaround targeted material IP specifically. A
prohibition framed around material IP qualifies.
