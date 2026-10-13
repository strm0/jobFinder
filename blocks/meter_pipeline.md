<!-- DEMO DATA. Maren Kjeldsen is an invented candidate and every detail in this file is made up. -->

# Meter readings pipeline

The data side of Maren's current job: the one developer and analyst at a small energy advice
company in Uppsala, where she has worked for five years. Source:
`context/candidate_brief.md`, sections "Who" and "What she can do".

This is paid work with an employer behind it, so it goes in Experience. The same employer is
also the source of the blocks in `followup_tool.md`. Both files use `source: energy_advice`,
and the source appears once per CV: pick one role summary, then take bullets from either file.

The CV entry header is `### Developer and analyst | Energy advice company, Uppsala`, with no
date line. Both role summaries say "five years", which is all the brief gives. See "Not
claimed here" in `identity.md`.

---

## Role summaries

### role-summary-data
```yaml
type: role_summary
source: energy_advice
lanes: [L1, L2, L6]
competency: [data_pipelines, reporting, internal_tooling]
register: [commercial, technical]
strength: strong
numbers: [5]
evidence: "context/candidate_brief.md, Who, third and fourth paragraphs"
interview_exposure: "Who reviewed the work, and why she is leaving. She is the one developer there, so no colleague in her own trade has reviewed it. The company is too small to grow in and she wants colleagues in her trade. Say it as the reason for applying, not as an apology."
```
**short:** The one developer and analyst at a small energy advice company for five years: built its reporting pipeline, its internal tools and its dashboards.

**long:** Five years as the one developer and analyst at a small energy advice company. Built its reporting pipeline, its internal tools and its dashboards, and is the person the advisers ask when a number looks wrong.

---

## Bullets

### pipeline-nightly
```yaml
type: bullet
source: energy_advice
lanes: [L1, L2]
competency: [data_pipelines, python, sql, automation]
register: [technical, commercial]
strength: strong
numbers: [3]
evidence: "context/candidate_brief.md, What she can do, Data pipelines, end to end"
interview_exposure: "How large the data is. Small, on one server. What the three suppliers' readings look like and what goes wrong in them. What happens when a night's run fails. Have a concrete answer for each."
```
**short:** Built a nightly pipeline in Python and SQL that collects meter readings from three suppliers, cleans them and loads them into PostgreSQL.

**long:** Built and runs a nightly pipeline in Python and SQL. It collects meter readings from three suppliers, cleans them and loads them into PostgreSQL, with dbt models on top.

---

### pipeline-dbt
```yaml
type: bullet
source: energy_advice
lanes: [L1]
competency: [data_modelling, sql]
register: [technical]
strength: adequate
numbers: []
evidence: "context/candidate_brief.md, What she can do, Data pipelines, end to end"
interview_exposure: "Which tests, and what one of them caught. dbt on one PostgreSQL server is not dbt on a cloud warehouse. Say so if the posting assumes one."
```
**short:** Wrote dbt models with tests on top of the loaded readings.

**long:** Same.

---

### pipeline-scheduling
```yaml
type: bullet
source: energy_advice
lanes: [L1, L2]
competency: [data_pipelines, automation]
register: [technical]
strength: adequate
numbers: []
evidence: "context/candidate_brief.md, What she can do, Data pipelines, end to end"
interview_exposure: "Why Airflow for one pipeline, and how it is run. One server, and she is its only operator. Have the real reason ready."
```
**short:** Set up and runs the Airflow scheduling for the pipeline.

**long:** Same. Use where the posting names orchestration or Airflow.

---

### dashboards
```yaml
type: bullet
source: energy_advice
lanes: [L1, L6, L7]
competency: [dashboards, reporting, data_visualisation]
register: [commercial, technical]
strength: adequate
numbers: []
evidence: "context/candidate_brief.md, Who, third paragraph, and What she can do, Charts and maps for people who are not analysts"
interview_exposure: "Who reads them and what they changed. No count of dashboards or users is in the bank."
```
**short:** Built the company's dashboards in Power BI and Metabase.

**long:** Same.

---

### monthly-report
```yaml
type: bullet
source: energy_advice
lanes: [L1, L2, L6]
competency: [reporting, automation]
register: [commercial]
strength: adequate
numbers: []
evidence: "context/candidate_brief.md, What she can do, Internal tools"
interview_exposure: "How many municipal customers. The bank holds no figure, so do not give one in writing."
```
**short:** Built the monthly reports to municipal customers, generated from templates.

**long:** Same. For L6 postings this is the bullet that shows she has delivered to municipalities as customers. She has not worked inside one.

---

## Not claimed here

- **No cloud data platform in production.** No Azure, AWS, Snowflake, Databricks, Spark or Kafka beyond courses. No BigQuery, Redshift or GCP. The warehouse is one PostgreSQL database on one server.
- **No scale.** Small data. Never write "large-scale", "big data" or "high-volume". The bank holds no row count, so do not write one.
- **No streaming or real-time processing.** The pipeline is a nightly batch.
- **No data engineer or analytics engineer job title.** She is the company's one developer and analyst. The work may be described as data engineering. The title may not.
- **No team, no staff, no budget.** She is the one developer. She has led work and never people. Do not write "led a team", "managed", "team lead" or "collaborated with data engineers".
- **One small employer.** All the data work is here. No large organisation, steering group, procurement or formal project model. Do not write "enterprise" or "stakeholder management across the organisation".
- **No experience inside a municipality or agency.** Municipalities were customers of the company.
- **No machine learning, forecasting or statistical modelling** on the meter data.
- **No claim about what the pipeline replaced.** The brief does not say how the readings were handled before.
- **No figures beyond three suppliers and five years.** No time saved, no error rate, no number of reports, customers, dashboards or users. If a figure would help, the candidate has to supply it and it becomes a block first.
- **No employer name and no calendar dates.** See `identity.md`.
