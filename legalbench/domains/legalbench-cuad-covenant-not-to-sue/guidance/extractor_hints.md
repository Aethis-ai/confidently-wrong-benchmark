# Subject-matter-expert guidance for the CUAD covenant-not-to-sue extractor.
#
# These are practitioner-level notes for the runtime LLM extractor that
# reads each contract clause and decides whether the two prongs of the
# covenant-not-to-sue test are present. They are written in plain
# English, do not reference any LegalBench case, label, or output from
# any model run against this benchmark, and are derived from
# (i) the Atticus Project's CUAD v1 taxonomy of contract-clause types,
# which defines "Covenant Not To Sue" as a category;
# (ii) standard contract-drafting treatises — Stark's *Drafting Effective
# Contracts*; *Negotiating and Drafting Contract Boilerplate*; Adams'
# *A Manual of Style for Contract Drafting*.
#
# Methodology note (per docs/heldout-methodology.md): these hints were
# added after observing the engine's first-pass behaviour on the dev
# half of the test split. The content is general — broader patterns
# of covenant-not-to-sue that the source's two-prong question can be
# read to encompass — not fitted to specific dev cases. Final score
# will be reported on the held-out half with these hints frozen.

## What counts as a "covenant not to sue" in commercial contracts

The CUAD taxonomy and standard contract-drafting practice recognise
several drafting patterns as covenants not to sue. The classification
question's two prongs ("contesting IP validity" / "bringing unrelated
claims") should be read to encompass each of the following common
patterns; recognise them when reading clauses:

### Prong 1 — restricts contesting IP validity

This includes any clause that constrains a party from challenging,
contesting, attacking, opposing, denying, or impairing the
counterparty's rights in intellectual property. Common drafting
forms:

- **Non-challenge / no-contest** language: *"shall not contest"*,
  *"shall not challenge the validity"*, *"shall not attack"*, *"shall
  not deny"*, *"shall not dispute"* the trademark, copyright, patent,
  or other IP.
- **Non-registration / non-assertion**: clauses preventing a party
  from registering, applying for, or asserting ownership of the
  counterparty's IP — *"shall not register"*, *"shall not apply for
  registration"*, *"shall not seek any rights in"*, *"shall not
  represent that it has an ownership interest"*.
- **No-impairment / no-tarnish**: clauses prohibiting acts that
  impair, dilute, or tarnish the counterparty's IP value.
- **Termination triggered by contesting IP**: clauses making
  contesting IP a termination event are a form of restriction
  (deterrent rather than prohibition, but functionally the same).
- **Acknowledgements of validity**: clauses that have a party
  affirmatively acknowledge the counterparty's rights, especially
  combined with non-contest language.

### Prong 2 — restricts otherwise bringing claims

This includes any clause that constrains a party from bringing
suit, filing claims, or pursuing legal action for matters beyond
the contract itself. Common drafting forms:

- **Direct prohibitions on suit / claim**: *"shall not bring a
  claim"*, *"shall not file"*, *"may not bring an action"*, *"is
  precluded from"*.
- **Releases**: general releases of claims, mutual releases,
  release-on-termination clauses. Releases bar future suits as a
  matter of contract.
- **Waivers of trial-related rights**: jury trial waivers, class
  action waivers, waiver of rights to specific procedural remedies.
  These restrict the manner in which claims can be brought.
- **Limitation periods / time bars**: contractual limitation periods
  shorter than statutory ones (e.g. *"no claim more than two years
  after"*) restrict bringing claims.
- **Dispute-resolution preambles** that exclude litigation: *"the
  parties desire to resolve disputes without litigation"*, *"all
  disputes shall be resolved by arbitration"*, *"no party shall
  initiate litigation"*.
- **Covenants of non-suit conditional on indemnification**: *"except
  for claims under [indemnification], neither party may bring a
  claim"* — the carve-out for indemnification doesn't defeat the
  general restriction.

## Edge-case reasoning

A clause can satisfy a prong even if the restriction is conditional,
mutual, or has carve-outs. The relevant question is whether the
clause's substantive effect is to constrain (in some material way)
the party's ability to contest IP or bring claims. Narrow exceptions
do not defeat the classification.

Conversely, a clause that *grants* a party rights, *assigns*
ownership, or *transfers* claims does not by itself create a covenant
not to sue — those are property-disposition clauses, not constraints
on suit.
