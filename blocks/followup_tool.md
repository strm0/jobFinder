<!-- DEMO DATA. Maren Kjeldsen is an invented candidate and every detail in this file is made up. -->

# Adviser follow-up tool and integrations

The tools side of Maren's current job at the energy advice company. Source:
`context/candidate_brief.md`, section "What she can do", paragraph "Internal tools".

Same employer as `meter_pipeline.md`, so the same `source: energy_advice` and the same CV
entry header. The source appears once per CV. For a web development or automation posting,
use the role summary here and lead with these bullets. For a data posting, use the one in
`meter_pipeline.md`.

---

## Role summary

### role-summary-builder
```yaml
type: role_summary
source: energy_advice
lanes: [L2, L3, L4]
competency: [internal_tooling, frontend, integration]
register: [technical, commercial]
strength: strong
numbers: [5]
evidence: "context/candidate_brief.md, Who, third and fourth paragraphs, and What she can do, Internal tools"
interview_exposure: "Whether anyone reviewed her code. She is the one developer there, so no colleague in her trade has. She wants colleagues in her own trade and a product more people use. Say it as a reason for applying, not as an apology."
```
**short:** The one developer at a small energy advice company for five years: builds its internal tools and the integrations between its systems.

**long:** Five years as the one developer and analyst at a small energy advice company. Builds its internal tools: the follow-up tool the advisers work in every day, the monthly customer reports and the integrations between its booking, accounting and customer systems.

---

## Bullets

### followup-tool
```yaml
type: bullet
source: energy_advice
lanes: [L2, L3, L4]
competency: [internal_tooling, frontend, react, typescript]
register: [technical, commercial]
strength: strong
numbers: [5]
evidence: "context/candidate_brief.md, What she can do, Internal tools"
interview_exposure: "Five users is a small number and the interviewer will notice. The strength is that they use it daily. Expect: how it is deployed, how it handles two advisers editing the same customer, whether it has tests."
```
**short:** Built a customer follow-up tool in TypeScript and React, used daily by five advisers.

**long:** Built the customer follow-up tool that five advisers at the company use every day, in TypeScript and React.

---

### integrations
```yaml
type: bullet
source: energy_advice
lanes: [L2, L6]
competency: [integration, automation, apis]
register: [technical, commercial]
strength: adequate
numbers: []
evidence: "context/candidate_brief.md, What she can do, Internal tools"
interview_exposure: "Which systems, by product name. The bank does not name them, so the candidate answers this in the room. Expect: what happens when one of the APIs is down."
```
**short:** Built the integrations between the booking, accounting and customer systems through their APIs.

**long:** Same.

---

## Not claimed here

- **Not a product.** An internal tool with five users at one small company. Never write "product", "SaaS", "customers" or "users" in a way that suggests more.
- **No user research on this tool.** Her research methods are in `skills.md` and the study with households is in `thesis.md`. The brief does not say she ran a study with the advisers, so do not write that she did.
- **No named systems.** "The booking, accounting and customer systems" is all the bank holds. Do not insert a product name because the posting mentions one, and do not write "CRM" or "ERP" as if the brief had.
- **No claim about what the integrations achieved.** The brief says they exist. It gives no time saved and does not say what was done by hand before.
- **No backend framework, database, hosting, authentication or testing claims for the tool.** The brief gives TypeScript and React and nothing more about how it is built or run. Do not attach PostgreSQL to it because the pipeline uses it.
- **No cloud platform.** Nothing here runs on Azure or AWS as far as the brief says.
- **No mobile app.** It is a web tool.
- **No team, no staff, no budget.** She is the one developer. Do not write "led", "managed" or "tech lead".
- **One small employer.** No large organisation, procurement or formal project model behind this work.
- **No figures beyond five advisers and five years.** No time saved, no number of customers followed up, no count of integrations beyond the three kinds of system named.
