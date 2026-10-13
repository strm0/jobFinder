<!-- DEMO DATA. Maren Kjeldsen is an invented candidate and every detail in this file is made up. -->

# Identity

Header, contact details, languages and eligibility. Appears on every CV.
Source: `context/candidate_brief.md`, sections "Who", "What rules a job out" and "What she can
do".

The contact details are placeholders. `example.com` is a reserved domain and the phone number
is all zeros, so neither can reach anyone.

---

### header-name
```yaml
type: skill_term
source: identity
lanes: [L1, L2, L3, L4, L5, L6, L7, phd]
competency: []
register: [commercial, technical, academic]
strength: strong
numbers: []
evidence: "context/candidate_brief.md, Who"
interview_exposure: "None."
```
**short:** Maren Kjeldsen

**long:** Same.

---

### header-title
```yaml
type: skill_term
source: identity
lanes: [L1, L2, L3, L4, L5, L6, L7, phd]
competency: []
register: [commercial, technical, academic]
strength: strong
numbers: []
evidence: "context/candidate_brief.md, Who, third paragraph"
interview_exposure: "If the line echoes the posting's title, expect to be asked whether she has held it. The two roles in the bank are web developer at an agency and the one developer and analyst at an energy advice company. Anything else describes the work, not a title."
```
**short:** Written fresh per posting, not selected. Describe the work the posting is about, or use the lane default below.

**long:** The line under the name is written per posting. It describes what she does. It is not a job title she has held, unless it is one of the two in the bank. Defaults if nothing better fits:

- L1: Data pipelines and reporting
- L2: Automation and integration
- L3: Web and application developer
- L4: Interaction designer who builds
- L5 and phd: Master's in human-computer interaction
- L6: Developer and analyst, data and digital services
- L7: Data visualisation

---

### header-contact
```yaml
type: skill_term
source: identity
lanes: [L1, L2, L3, L4, L5, L6, L7, phd]
competency: []
register: [commercial, technical, academic]
strength: strong
numbers: []
evidence: "Placeholder contact details, invented for the demo"
interview_exposure: "None."
```
**short:** Uppsala, Sweden | +46 00 000 00 00 | maren@example.com

**long:** Same. No website, portfolio or code repository link is in the bank, so none is added.

---

### languages
```yaml
type: skill_term
source: identity
lanes: [L1, L2, L3, L4, L5, L6, L7, phd]
competency: []
register: [commercial, technical, academic]
strength: strong
numbers: []
evidence: "context/candidate_brief.md, What rules a job out, Language, and What she can do, Languages"
interview_exposure: "Part of the interview may be held in Swedish or Danish to check. That is fine. Her written Swedish is good, not native. If the job is mostly writing Swedish for the public, say so before they find out."
```
**short:** Danish (first language), Swedish (fluent in speech, good in writing), English (working language).

**long:** Danish is her first language. Swedish is fluent in speech and good in writing. English is a working language. She works in all three. Where a posting in Sweden asks for Danish, move this into the profile paragraph: it is rare there and worth leading with.

---

### eligibility
```yaml
type: skill_term
source: identity
lanes: [L1, L2, L3, L4, L5, L6, L7, phd]
competency: []
register: [commercial, technical, academic]
strength: strong
numbers: [9]
evidence: "context/candidate_brief.md, Who, and What rules a job out, Citizenship"
interview_exposure: "Whether she can take a post in a security class. She cannot, and she cannot hold a post open only to Swedish citizens. An ordinary background check is a different thing and is no obstacle. Say so before the employer finds out."
```
**short:** Danish citizen. Driving licence.

**long:** Danish citizen, nine years in Sweden. Holds a driving licence. Include only where the posting asks about citizenship, residence or a licence.

---

## Profile anchors

Calibration examples for the profile paragraph. Not text to insert. See SCHEMA.md section 6.

### anchor-L1-L2
```yaml
type: profile_anchor
lanes: [L1, L2]
register: [commercial, technical]
```
Developer and analyst with eight years of work, five of them as the one developer at an energy advice company in Uppsala. Built its nightly pipeline in Python and SQL into PostgreSQL, put tested dbt models on top, runs the scheduling in Airflow, and built the follow-up tool five advisers use every day. Works in Swedish, Danish and English.

---

### anchor-L3
```yaml
type: profile_anchor
lanes: [L3]
register: [commercial, technical]
```
Web and application developer with eight years of work and a bachelor's in software development. Three years of client sites and small web applications at a web agency, in JavaScript and PHP on a headless CMS, then five years building a company's internal tools in TypeScript and React. Works in Swedish, Danish and English.

---

### anchor-L4-L7
```yaml
type: profile_anchor
lanes: [L4, L7]
register: [commercial, academic]
```
Developer and analyst with a master's in human-computer interaction. Her thesis tool, a visualisation of household energy data, was tested with twelve households, and she makes dashboards, custom charts and maps for readers who are not analysts. Works in Swedish, Danish and English.

---

## Not claimed here

- **No real contact details.** The address, the phone number and the name are invented. Do not replace them with anything that looks real.
- **No website, portfolio, LinkedIn or GitHub link.** The brief names none.
- **No job title beyond the two the brief gives.** Web developer at an agency, and the one developer and analyst at the energy advice company. The header line describes the work. Never write "Data Engineer", "Analytics Engineer", "UX Designer" or "Tech Lead" as a title she has held.
- **No employer names and no calendar dates for the jobs.** The brief says "an agency" and "a small energy advice company in Uppsala", and gives lengths: three years and five years. Write the organisations as "Web agency" and "Energy advice company, Uppsala". The lengths may be written. Start and end years may not, because the brief gives none.
- **Eight years of work, not more.** Three plus five. Do not round up, and do not write "senior", "lead", "principal" or "head of" as a level she holds. A posting that asks for ten years or more is a gap for `notes.md`.
- **No staff or budget responsibility.** She has led work and never people. Never write "manager", "team lead" or "personalansvar".
- **No large organisation.** The five years of data and tools work are at one small employer. No steering groups, procurement or formal project models.
- **No cloud data platform in production.** See `skills.md` and `meter_pipeline.md`.
- **Swedish is her second language.** Never write "native Swedish" or "all three at native level". The wording in the `languages` block is the wording to use.
- **No fourth working language.** She reads Norwegian. That is not a working language and is not listed as one.
- **No Swedish citizenship.** She cannot take a post in a security class or one open only to Swedish citizens. Never write "eligible for security clearance".
- **Not a student.** Both degrees are finished. She is not eligible for a post that requires current enrolment.
- **No doctorate and no professional licence or authorisation.**
