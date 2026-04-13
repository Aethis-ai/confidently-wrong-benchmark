# English Language Requirement — British Nationality Act 1981

> **Source:** British Nationality Act 1981, Schedule 1, Paragraph 1(1)(c); Form AN Guidance (September 2025)
>
> **Purpose:** This document defines the "knowledge of language" requirement for naturalisation
> as a British citizen. This is a separate, independent requirement from the Life in the UK test.

## Section 1: Statutory basis

The requirement derives from the British Nationality Act 1981, Schedule 1, Paragraph 1(1)(c):

> "that the applicant has sufficient knowledge of the English, Welsh or Scottish Gaelic language"

This is one of the conditions that must be satisfied before the Secretary of State may
grant a certificate of naturalisation.

## Section 2: Majority English Speaking Country (MESC) nationality route

(1) An applicant who is a national of a majority English speaking country automatically
satisfies the English language requirement.

(2) The following countries are accepted as majority English speaking countries for
naturalisation purposes:

- Antigua and Barbuda
- Australia
- The Bahamas
- Barbados
- Belize
- The British overseas territories
- Canada
- Dominica
- Grenada
- Guyana
- Ireland (for citizenship only)
- Jamaica
- Malta
- New Zealand
- St Kitts and Nevis
- St Lucia
- St Vincent and the Grenadines
- Trinidad and Tobago
- The United States of America

(3) IMPORTANT: Canada is classified as a majority English speaking country for the
NATIONALITY route (a Canadian national automatically meets the language requirement).
However, Canada is NOT classified as a majority English speaking country for the DEGREE
route — because Canada is officially bilingual, a Canadian degree requires BOTH an AQUALS
and an ELPS certificate, the same as any non-MESC country degree.

## Section 3: UK degree route

(1) An applicant who holds a UK academic qualification equivalent to a UK Bachelor's
degree, Master's degree, or PhD, which was taught in English, satisfies the English
language requirement.

(2) The applicant must provide their degree certificate.

(3) Note: The applicant still needs to pass the Life in the UK test separately.

## Section 4: MESC country degree route

(1) An applicant who holds a degree from a majority English speaking country (EXCLUDING
Canada) may satisfy the English language requirement with ONLY an Academic Qualification
Level Statement (AQUALS) from Ecctis confirming equivalency.

(2) An ELPS (English Language Proficiency Statement) is NOT required for degrees from
MESC countries (excluding Canada), because these countries are considered to teach
primarily in English.

## Section 5: Non-MESC and Canadian degree route

(1) An applicant who holds a degree from a NON-majority English speaking country, or from
Canada (which is bilingual), must provide BOTH of the following:

- (a) An Academic Qualification Level Statement (AQUALS) from Ecctis confirming the
  qualification is equivalent to a UK qualification
- (b) An English Language Proficiency Statement (ELPS) from Ecctis showing that the
  degree was taught in English

(2) Canada is treated the same as non-MESC countries for the degree route because it is
an officially bilingual country (English and French). A Canadian degree may have been
taught in French, so ELPS confirmation is required.

## Section 6: Secure English Language Test (SELT) route

(1) An applicant may satisfy the English language requirement by passing an approved
Secure English Language Test (SELT) at CEFR level B1 or higher (B1, B2, C1, or C2).

(2) The test must be taken at a Home Office approved test centre.

(3) Sub-route A — Settlement reuse: If the applicant successfully used a B1+ SELT
qualification to obtain indefinite leave to remain (settlement), that same qualification
may be reused for the naturalisation application. There is NO time limit on reuse of a
SELT used for settlement.

(4) Sub-route B — Recent SELT: If the applicant has a B1+ SELT qualification that was
NOT used for settlement, the test must have been taken within the last 2 years. Test
results older than 2 years are not valid.

(5) SELT qualifications below B1 level (A1, A2) do NOT satisfy the requirement.

## Section 7: Age exemption

(1) An applicant who is aged 65 or over at the date of application is exempt from the
English language requirement.

(2) An applicant who is under the age of 18 at the date of application is exempt from
the English language requirement.

## Section 8: Medical exemption

(1) An applicant who has a long-term physical or mental condition that permanently
prevents them from meeting the English language requirement may be exempt.

(2) Temporary conditions (such as depression or stress) do not normally qualify.

(3) The applicant must provide evidence from a registered medical practitioner.

## Section 9: Discretionary waiver

(1) The Secretary of State may, under s.6(2) of the British Nationality Act 1981, waive
the English language requirement at their discretion in exceptional circumstances.

(2) This is extremely rarely exercised.

## Section 10: Summary of routes

Any ONE of the following routes satisfies the English language requirement:

| Route | Requirement | Key fields |
|-------|-------------|------------|
| MESC nationality | National of a MESC country | nationality |
| UK degree | UK degree at Bachelor's+ taught in English | has_academic, degree_country |
| MESC degree | MESC country degree (excl. Canada) + AQUALS | has_academic, degree_country, ecctis_aquals |
| Non-MESC/Canadian degree | Degree + AQUALS + ELPS | has_academic, degree_country, ecctis_aquals, ecctis_elps |
| SELT (settlement) | B1+ SELT used for settlement | has_selt, selt_level, settlement_selt_used |
| SELT (recent) | B1+ SELT within 2 years | has_selt, selt_level, selt_within_two_years |
| Age exemption | Under 18 or 65+ | age |
| Medical exemption | Long-term condition | medical_exempt |
| Discretion | Secretary of State waiver | discretion_applied |
