# LegalBench task: `hearsay`

Source: [HazyResearch/legalbench tasks/hearsay/README.md](https://github.com/HazyResearch/legalbench/blob/main/tasks/hearsay/README.md)
License: CC BY 4.0
Source author: Neel Guha

The text below is the `## Task description` section of the LegalBench
`hearsay` README, reproduced verbatim. It is the same canonical rule
statement that frontier-LLM baselines published against this task have
been evaluated on. No paraphrase, no editorial choices.

---

## Task description
The Federal Rules of Evidence dictate that hearsay evidence is inadmissible at trial. Hearsay is defined as an "out-of-court statement introduced to prove the truth of the matter asserted." In determining whether a piece of evidence meets the definition of hearsay, lawyers ask three questions: 

1. Was there a statement?
2. Was it made outside of court?
3. Is it being introduced to prove the truth of the matter asserted?

**Was there a statement?** The definition of statement is broad, and includes oral assertions, written assertions, and non-verbal conduct intended to communicate (i.e. \textit{assert}) a message. Thus, for the purposes of the hearsay rule, letters, verbal statements, and pointing all count as statements. 

**Was it made outside of court?** Statements not made during the trial or hearing in question count as being out-of-court. 

**Is it being introduced to prove the truth of the matter asserted?** A statement is introduced to prove the truth of the matter asserted if its truthfulness is essential to the purpose of its introduction. Suppose that at trial, the parties were litigating whether Alex was a soccer fan. Evidence that Alex told his brother "I like soccer," would be objectionable on hearsay grounds, as (1) the statement itself asserts that Alex likes soccer, and (2) the purpose of introducing this statement is to prove/disprove that Alex likes soccer. In short, the truthfulness of the statement's assertion is central to the issue being litigated. However, consider if one of the parties wished to introduce evidence that Alex told his brother, "Real Madrid is the greatest soccer team in the world." This statement would **not** be hearsay. Its assertion---that Real Madrid is the greatest soccer team in the world---is unrelated to the issue being litigated. Here, one party is introducing the statement not to prove what the statement says, but to instead show that a particular party (i.e. Alex) was the speaker of the statement.

In practice, many pieces of evidence which are hearsay are nonetheless still admissible under one of the many hearsay exception rules. We ignore these exceptions for our purposes, and leave the construction of benchmarks corresponding to these exceptions for future work.

