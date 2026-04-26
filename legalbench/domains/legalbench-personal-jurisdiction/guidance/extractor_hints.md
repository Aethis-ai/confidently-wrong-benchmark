# Subject-matter-expert guidance for the personal-jurisdiction extractor.
#
# These are textbook personal-jurisdiction analysis principles, derived
# from standard federal civil-procedure treatment (Hazard / Tait /
# Fletcher; Wright & Miller; the cases in the International Shoe →
# Hanson v. Denckla → World-Wide Volkswagen → Burger King line).
# They are written in plain English, do not reference any LegalBench
# case, label, or output from any model run against this benchmark.

## Identify the forum first

When reading a fact pattern that ends with "Plaintiff sues Defendant in
[STATE]", **STATE** is the **forum**. All three jurisdictional elements
are evaluated against the forum:

- `defendant_domiciled_in_forum`: does the defendant live in the FORUM
  state? Not in some other state where they happen to do business or
  visit.
- `defendant_has_sufficient_contacts_with_forum`: are the defendant's
  contacts with the FORUM state sufficient? Not their contacts with
  some other state.
- `claim_arises_from_contacts_with_forum`: does the claim arise out of
  the defendant's contacts with the FORUM state?

A defendant who lives in State A, runs a business in State B, and is
sued in State C is **not** automatically subject to jurisdiction in
State C just because they have ties to A or B. The analysis is forum-
specific.

## What counts as "sufficient contacts"

Personal jurisdiction's "minimum contacts" doctrine recognises a wide
range of forum-directed activity as sufficient when the claim arises
out of that activity:

- **Physical presence in the forum, even briefly.** A defendant who
  takes a tortious action while physically in the forum (gets in a
  fight, commits a fraud, signs a contract) has thereby availed
  themselves of the forum's laws. The visit can be short.
- **Selling or shipping products into the forum.** Marketing, taking
  orders from forum residents, or delivering goods into the forum.
- **Targeting forum residents with solicitation.** An unsolicited
  phone call, email, or advertisement directed at a forum resident
  counts as a contact with the forum, even if the defendant has never
  physically been there.
- **Doing business with forum residents who travelled to the
  defendant.** This is more contested; but under the rule's "purposeful
  availment" formulation, knowingly transacting with a forum resident
  AND knowing the resident will return to the forum can establish
  contacts (especially when combined with marketing into the forum).

By contrast, **incidental or random contacts** are not sufficient: a
defendant whose contact with the forum is solely the unilateral act
of the plaintiff (e.g. the plaintiff happens to live there), or who
has only fortuitous connections, generally lacks sufficient contacts.

**Contacts are evaluated as of the time of the relevant conduct, not
the time of suit.** A defendant who operated in or directed activity
at the forum at the time the cause of action arose has forum contacts
for that claim, even if the defendant later moved away, dissolved the
business, or otherwise severed ongoing ties. Subsequent relocation
does not retroactively erase past forum contacts.

## "Arising out of" / nexus

Nexus is satisfied when the cause of action **arises directly from**
the defendant's forum contacts:

- A tort committed in the forum gives nexus with the forum for that
  tort.
- A defective product sold into the forum and which causes injury in
  the forum gives nexus.
- Breach of a contract negotiated, performed, or directed into the
  forum gives nexus.

Nexus is **not** satisfied when the claim is unrelated to the
defendant's forum contacts: a defendant who has business in the forum
on unrelated matters cannot be sued there for a claim that arose
elsewhere and has nothing to do with those forum activities.

If the defendant has no contacts with the forum at all, set
`claim_arises_from_contacts_with_forum` to false (the prong is
vacuously unmet).

## Domicile vs. doing business

Domicile means **living in** the state — being a citizen / resident
of it. A person can be domiciled in State A while running a business
in State B; in that case, B is not their domicile. Conversely, a
defendant who operates a business in the forum but lives elsewhere is
not domiciled in the forum (though their business activity may
establish contacts).

A corporation's principal place of business and state of incorporation
can establish corporate domicile, but for individual defendants
domicile follows residence/citizenship, not business operations.

## Defendants with no forum link

If, after going through the above, the defendant has no domicile in
the forum and no qualifying contacts with the forum, both contact
prongs are false and there is no personal jurisdiction. This is the
most common "no contacts" case shape.
