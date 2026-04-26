# LegalBench task: `personal_jurisdiction`

Source: [HazyResearch/legalbench tasks/personal_jurisdiction/README.md](https://github.com/HazyResearch/legalbench/blob/main/tasks/personal_jurisdiction/README.md)
License: CC BY 4.0
Source: Neel Guha (LegalBench)

The text below is the `## Task description` section of the LegalBench
`personal_jurisdiction` README, reproduced verbatim. It is the same
canonical rule statement that frontier-LLM baselines published against
this task have been evaluated on. No paraphrase, no editorial choices.

---

## Task description

Personal jurisdiction refers to the ability of a particular court (e.g. a court in the Northern District of California) to preside over a dispute between a specific plaintiff and defendant~\todocite. A court (sitting in a particular forum) has personal jurisdiction over a defendant only when that defendant has a relationship with the forum. We focus on a simplified version of the rule for federal personal jurisdiction, using the rule:

```text
There is personal jurisdiction over a defendant in the state where the defendant is domiciled, or when (1) the defendant has sufficient contacts with the state, such that they have availed themselves of the privileges of the state and (2) the claim arises out of the nexus of the defendant's contacts with the state.
```

Under this rule, there are two paths for a court have jurisdiction over a defendant: through domicile or through contacts.

- **Domicile**: A defendant is domiciled in a state if they are a citizen of the state (i.e. they live in the state). Changing residency affects a change in citizenship.
- **Contacts**:  Alternatively, a court may exercise jurisdiction over a defendant when that defendant has *sufficient contacts* with the court's forum, and the legal claims asserted arise from the \textit{nexus} of the defendant's contacts with the state. In evaluating whether a set of contacts are sufficient, lawyers look at the extent to which the defendant interacted with the forum, and availed themselves of the benefits and privileges of the state's laws. Behavior which usually indicates sufficient contacts include: marketing in the forum or selling/shipping products into the forum. In assessing nexus, lawyers ask if the claims brought against the defendant arise from their contacts with the forum. In short: is the conduct being litigated involve the forum or its citizens in some capacity?

