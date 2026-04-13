# CAR Policy Defect Exclusion Endorsement Schedule 2025

## Synthetic Policy Wording — Controlled Test Fixture

> **Purpose:** This document is a synthetic insurance endorsement designed to exercise every
> pattern supported by the TDA eligibility engine. It serves as a closed-loop regression
> anchor — the wording never changes, so any engine regression is immediately detectable.
> It is modelled on the structure and language of London market Construction All Risks
> (CAR) policy wordings, specifically the DE3/DE5 defect exclusion clause structure and
> LEG3/06 endorsement patterns used for major infrastructure projects.

> **Named Project:** Thames Estuary Resilience Tunnel (fictional)

---

## Part 1 — General Provisions

### Clause 1: Title and effective date

(1) This endorsement may be cited as the CAR Policy Defect Exclusion
    Endorsement Schedule 2025.

(2) This endorsement is effective from 1 March 2025.

### Clause 2: Interpretation

In this endorsement—

- "the Works" means all permanent and temporary works forming part of the
  insured contract, including materials on site;
- "defective component" means any part of the Works that is defective in
  design, plan, specification, materials, or workmanship;
- "rectification cost" means the cost of repairing, replacing, or rectifying
  a defective component;
- "access damage" means damage caused solely to gain access to, remove, or
  replace a defective component;
- "resultant damage" means physical loss of or damage to other insured property
  that was not itself defective before the event and was damaged as a physical
  consequence of the defective component failing;
- "enhanced cover project" means a project with a total insured value of not
  less than GBP 100 million;
- "pioneer infrastructure project" means a project with a total insured value
  of not less than GBP 500 million;
- "JCT-compliant contract" means a construction contract that complies with
  the Joint Contracts Tribunal standard form or an equivalent approved form.

---

## Part 2 — Coverage Determination

### Clause 3: Policy period

*[Pattern: UNSAT early termination — disqualifying condition]*

(1) This endorsement applies only to loss or damage occurring within the
    policy period.

(2) Where loss or damage occurs outside the policy period, the claim must
    be refused without consideration of any other clause under this
    endorsement.

> **Engine pattern:** `period_valid == true`. If period_valid = false, the outcome is
> immediately UNSAT — no further questions are asked.

---

### Clause 4: Insuring clause

*[Pattern: Multi-field AND — all sub-conditions must be satisfied]*

(1) The insured must demonstrate that the following conditions are both
    satisfied—

    (a) physical loss of or damage to insured property has occurred; and

    (b) a defective component has been identified in connection with the loss.

(2) A claim that does not establish both physical loss and the presence of
    a defective component is not within the scope of this endorsement.

> **Engine pattern:** `And(is_physical == true, is_defective == true)`
> within a single criterion in the `insuring_clause` group.

---

### Clause 5: Insured property categories

*[Pattern: ENUM field with IN operator — membership check]*

(1) This endorsement covers property falling within one of the following
    categories—

    (a) permanent works;

    (b) temporary works;

    (c) existing structures; and

    (d) materials on site.

(2) Plant and equipment is not covered under this endorsement. Cover for
    plant and equipment is provided under a separate section of the policy.

> **Engine pattern:** `property_category IN ["permanent_works", "temporary_works",
> "existing_structures", "materials_on_site"]`. Compiled to
> `Or(EQ(category, v1), EQ(category, v2), EQ(category, v3), EQ(category, v4))`.

---

### Clause 6: Defect rectification exclusion

*[Pattern: Absolute exclusion — unconditional AND term, no override possible]*

(1) The cost of repairing, replacing, or rectifying any component that is
    itself defective in design, plan, specification, materials, or
    workmanship is excluded absolutely.

(2) For the avoidance of doubt, the exclusion under subclause (1) applies
    regardless of—

    (a) the project value;

    (b) whether enhanced cover or pioneer infrastructure provisions apply;

    (c) the origin of the defect; or

    (d) any carve-back under Clause 7.

(3) No other provision of this endorsement reinstates cover for
    rectification costs.

> **Engine pattern:** `is_rectification == false` in the `not_rectification` group.
> This is an unconditional AND term in the outcome logic — the insurance equivalent
> of the Vogon species exclusion. No carve-back, enhanced cover, or pioneer override
> can save a rectification claim.

---

### Clause 7: Carve-back for resultant damage

*[Pattern: Multi-route OR — alternative satisfaction paths]*

(1) Where the claim is not for rectification costs (Clause 6), cover for
    damage to other insured property may be established via one of the
    following routes—

    (a) **Route A (LEG3 endorsement):** the damage arose as a physical
        consequence of the defective component failing; or

    (b) **Route B (DE3 wording):** the claim is for damage that was not
        caused solely to gain access to, remove, or replace the defective
        component.

(2) Satisfaction of either route under subclause (1) is sufficient for
    the purposes of this clause.

(3) Property is not to be treated as damaged merely because a defect
    exists within it.

> **Engine pattern:** Two criteria in the `carveback_qualification` group.
> Within-group semantics are OR — either route satisfies the group.
> Route A requires affirmative proof of causal consequence.
> Route B requires only that the damage is not access/removal damage.
> A claim with `consequence_of_failure=false, is_access_damage=false` passes
> Route B but not Route A — this is the DE3/LEG3 coverage gap that brokers
> argue about in practice.

---

### Clause 8: Access and removal damage re-exclusion

*[Pattern: Gate for three-level exception chain]*

(1) Notwithstanding Clause 7, damage caused solely to gain access to,
    remove, or replace the defective component is excluded, subject to
    Clause 9.

(2) For the avoidance of doubt, access damage means damage to property
    that was not itself defective but was damaged only because it was
    necessary to remove or disturb it in order to reach the defective
    component for repair or replacement.

> **Engine pattern:** `is_access_damage == true` in the `access_exclusion` group.
> This gates the three-level exception chain in Clause 9. If `is_access_damage`
> is false, the access exclusion is not triggered (vacuously resolved).

---

### Clause 9: Enhanced cover for large projects

*[Pattern: Three-level exception chain — "A except B excluding C"]*

(1) Subject to subclause (2), where the insured project is an enhanced
    cover project (total insured value of not less than GBP 100 million),
    the exclusion of access damage under Clause 8 does not apply.

(2) The enhanced cover under subclause (1) does not extend to access
    damage arising from a defect of design, unless subclause (3) applies.

(3) Where the insured project is a pioneer infrastructure project (total
    insured value of not less than GBP 500 million), the limitation under
    subclause (2) does not apply, and enhanced cover extends to access
    damage arising from all defect origins including design.

(4) For the avoidance of doubt—

    (a) a project valued at GBP 200 million with a workmanship defect:
        access damage IS covered under subclause (1);

    (b) a project valued at GBP 200 million with a design defect:
        access damage is NOT covered (subclause (2) applies);

    (c) a project valued at GBP 500 million with a design defect:
        access damage IS covered (subclause (3) overrides subclause (2));

    (d) a project valued at GBP 50 million:
        access damage is NOT covered regardless of defect origin
        (below enhanced cover threshold);

    (e) rectification costs remain excluded regardless of project value
        (Clause 6 is absolute).

> **Engine pattern:** Three-level exception chain:
>
> Level 1 (A): `project_value >= 100` → access damage covered
> Level 2 (B): `defect_origin == "design"` → exception: enhanced cover doesn't apply
> Level 3 (C): `project_value >= 500` → exception to the exception: pioneer overrides
>
> Outcome logic for access damage resolution:
> ```
> Or(
>   Not(access_exclusion),                    # Not access damage → no issue
>   And(
>     enhanced_cover,                         # A: project >= £100M
>     Or(
>       Not(design_defect_check),             # B: not a design defect
>       pioneer_override                      # C: or pioneer >= £500M overrides
>     )
>   )
> )
> ```

---

### Clause 10: Existing structures condition

*[Pattern: Nested IMPLIES — conditional requirement based on property category]*

(1) Where the property suffering loss or damage is an existing structure—

    (a) the principal contractor must have a JCT-compliant construction
        contract in place at the date of loss.

(2) Where the property is not an existing structure, no JCT-compliant
    contract is required for the purposes of this endorsement.

> **Engine pattern:** Two groups: `existing_structures_gate` (category ==
> "existing_structures") and `jct_compliance` (jct_compliant == true).
> Outcome logic: `Implies(existing_structures_gate, jct_compliance)`.
> If property is existing structures, JCT contract required.
> Otherwise, vacuous truth — JCT compliance is irrelevant.

---

### Clause 11: Notification compliance

*[Pattern: DATE-bounded requirement — temporal window check]*

(1) The insured must notify underwriters of any loss or damage within
    30 days of discovery.

(2) For the purposes of subclause (1), dates are expressed in days and
    notification is compliant where—

    notification_date - discovery_date <= 30

(3) Late notification renders the claim void under this endorsement.

> **Engine pattern:** `notification_within_period` (BOOL) pre-computed at intake.
> `notification_within_period == true` in the `notification` group.
> Until temporal helpers are implemented, this is a pre-computed BOOL field —
> the temporal check is done at intake, matching the spacecraft medical cert pattern.

---

## Part 3 — Determination of Coverage

### Clause 12: Overall coverage determination

(1) A claim is covered under this endorsement if and only if all of the
    following conditions are met—

    (a) the loss occurred within the policy period (Clause 3);

    (b) the insured has established physical loss and the presence of a
        defective component (Clause 4);

    (c) the property falls within an insured category (Clause 5);

    (d) the insured has notified underwriters within the required period
        (Clause 11);

    (e) where the property is an existing structure, a JCT-compliant
        contract is in place (Clause 10);

    (f) the claim is not for rectification of the defective component
        itself (Clause 6);

    (g) the claim qualifies under at least one carve-back route
        (Clause 7); and

    (h) where the damage is access damage (Clause 8), the enhanced cover
        provisions apply (Clause 9).

> **Outcome logic (AST):**
> ```
> And(
>   policy_period,
>   insuring_clause,
>   insured_category,
>   notification,
>   Implies(existing_structures_gate, jct_compliance),
>   not_rectification,
>   carveback_qualification,
>   Or(
>     Not(access_exclusion),
>     And(
>       enhanced_cover,
>       Or(
>         Not(design_defect_check),
>         pioneer_override
>       )
>     )
>   )
> )
> ```

---

## Appendix A — Field Registry

| Key | Sort | Question | Enum Values |
|-----|------|----------|-------------|
| `car.policy.period_valid` | BOOL | Did the loss occur within the policy period? | — |
| `car.property.category` | ENUM | What category of insured property suffered loss? | permanent_works, temporary_works, plant_equipment, existing_structures, materials_on_site |
| `car.loss.is_physical` | BOOL | Has physical loss of or damage to insured property occurred? | — |
| `car.component.is_defective` | BOOL | Has a defective component been identified? | — |
| `car.defect.origin` | ENUM | What is the origin of the defect? | design, specification, materials, workmanship, none |
| `car.claim.is_rectification` | BOOL | Is the claim for the cost of rectifying the defective component itself? | — |
| `car.claim.is_access_damage` | BOOL | Was damage caused solely to gain access to or remove the defective component? | — |
| `car.damage.consequence_of_failure` | BOOL | Did damage arise as a physical consequence of the defective component failing? | — |
| `car.project.value_millions_gbp` | INT | What is the total insured project value in GBP millions? | — |
| `car.notification.within_period` | BOOL | Was the loss notified to underwriters within 30 days of discovery? | — |
| `car.contract.jct_compliant` | BOOL | Is a JCT-compliant construction contract in place? | — |

## Appendix B — Groups and Outcome Logic

| Group Name | Criteria (OR within group) | Clause |
|------------|---------------------------|--------|
| `policy_period` | period_valid == true | Cl.3 |
| `insuring_clause` | And(is_physical, is_defective) | Cl.4 |
| `insured_category` | category IN [permanent_works, temporary_works, existing_structures, materials_on_site] | Cl.5 |
| `not_rectification` | is_rectification == false | Cl.6 |
| `carveback_qualification` | consequence_of_failure \| NOT(is_access_damage) | Cl.7 |
| `access_exclusion` | is_access_damage == true | Cl.8 |
| `enhanced_cover` | project_value >= 100 | Cl.9(1) |
| `design_defect_check` | defect_origin == "design" | Cl.9(2) |
| `pioneer_override` | project_value >= 500 | Cl.9(3) |
| `existing_structures_gate` | category == "existing_structures" | Cl.10 |
| `jct_compliance` | jct_compliant == true | Cl.10 |
| `notification` | within_period == true | Cl.11 |

## Appendix C — Pattern Coverage Matrix

| # | Pattern | Clause | Verified By |
|---|---------|--------|-------------|
| 1 | Multi-field AND | Cl.4 | `test_insuring_clause_*` |
| 2 | Multi-route OR | Cl.7 | `test_carveback_*` |
| 3 | Three-level exception chain (A except B excluding C) | Cl.9 | `test_enhanced_cover_*` |
| 4 | Nested IMPLIES | Cl.10 | `test_existing_structures_*` |
| 5 | UNSAT early termination | Cl.3 | `test_policy_period_*` |
| 6 | ENUM + IN operator | Cl.5 | `test_insured_category_*` |
| 7 | DATE-bounded validity period (pre-computed BOOL) | Cl.11 | `test_notification_*` |
| 8 | Override (exception to exception) | Cl.9(3) | `test_pioneer_override_*` |

## Appendix D — Demonstration Scenarios

### Thames Estuary Resilience Tunnel — Defective Steel Bracket

A tunnel project uses a defective steel bracket design in a ventilation assembly.

| | Case A | Case B | Case C |
|---|--------|--------|--------|
| **Scenario** | Bracket cracks before causing further damage | Bracket fails; ducting collapses and non-defective ceiling panels damaged | Contractors cut intact wall lining to access bracket for replacement |
| **Defective bracket** | Claim item | Not claimed | Not claimed |
| **Other damaged property** | None | Ducting + ceiling panels | Wall lining + surrounding panels |
| **Damage type** | Rectification | Consequence of failure | Access/removal |
| **Covered?** | **No** | **Yes** (other property only) | **No** |
| **Reason** | Rectification of defective component = absolute exclusion (Cl.6) | Resultant damage to non-defective property = carve-back applies (Cl.7a) | Access damage = re-excluded (Cl.8); standard project = no enhanced cover |

**Why LLMs fail:** Cases B and C both involve damage to non-defective surrounding
property, but only one is covered. The distinction is not surface similarity but the
reason the damage occurred — consequence of failure vs. enabling repair.
