<!-- DEMO DATA. Maren Kjeldsen is an invented candidate and every detail in this file is made up. -->

# Skills

The skill terms and the rule for assembling the Skills section. Source:
`context/candidate_brief.md`, section "What she can do", paragraphs "Web development",
"Design with users", "Charts and maps for people who are not analysts" and "Stack".

---

## Assembly rule

Two lines at most: one of methods, one of tools and technologies. Ten to fourteen terms per
line. Beyond that nobody reads it and the strong terms are diluted by the weak ones.

Order by relevance to the posting, not by the candidate's confidence. The first three terms
on each line are the only ones a skimming reader takes in.

**Never list a term that appears in no block.** If the posting asks for something the
candidate has and no block covers, that is a gap in the bank. The fix is to write the block,
not to add the word.

**Lane defaults.** L1 leads with data. L2 leads with automation and integration. L3 leads
with languages and frameworks. L4, L5 and phd lead with research methods. L6 leads with
reporting and integration. L7 leads with visualisation.

---

### skills-data
```yaml
type: skill_term
source: skills
lanes: [L1, L2, L6]
competency: [data_pipelines, sql, python]
register: [technical, commercial]
strength: strong
numbers: []
evidence: "context/candidate_brief.md, What she can do, Data pipelines, end to end, and Stack"
interview_exposure: "Scale. It is small data on one server: Airflow she set up and runs herself, dbt on PostgreSQL. Say so if the posting assumes a cloud platform."
```
**short:** Python, SQL, pandas, dbt, PostgreSQL, Airflow, Power BI, Metabase

**long:** Same. Order by the posting's own stack.

---

### skills-languages-frameworks
```yaml
type: skill_term
source: skills
lanes: [L3, L2, L7]
competency: [programming, frontend]
register: [technical]
strength: strong
numbers: []
evidence: "context/candidate_brief.md, What she can do, Stack"
interview_exposure: "Which of these are current. TypeScript, React, Python and SQL are what she uses now. PHP is evidenced by the agency years only. Say which is which."
```
**short:** TypeScript, JavaScript, Python, SQL, PHP, HTML and CSS, React, D3, Docker, git, Linux

**long:** Same. Order by the posting's own stack.

---

### skills-web
```yaml
type: skill_term
source: skills
lanes: [L3, L6]
competency: [web_development, accessibility]
register: [technical, commercial]
strength: adequate
numbers: []
evidence: "context/candidate_brief.md, What she can do, Web development"
interview_exposure: "Which headless CMS, and what the accessibility fixes were. The bank names no product and no standard, so the candidate answers both in the room."
```
**short:** Client sites and small web applications, headless CMS, accessibility fixes, handover to customers

**long:** Same. These are the terms from the agency years. Use on the methods line for a web posting.

---

### skills-methods
```yaml
type: skill_term
source: skills
lanes: [L4, L5, phd]
competency: [user_research, research_methods, usability_testing, prototyping]
register: [commercial, academic]
strength: strong
numbers: []
evidence: "context/candidate_brief.md, What she can do, Design with users"
interview_exposure: "Where she used each one. Have an example per method, and do not let the thesis stand for all four unless it did."
```
**short:** Interviews, contextual inquiry, moderated usability testing, prototyping in Figma

**long:** Same.

---

### skills-visualisation
```yaml
type: skill_term
source: skills
lanes: [L7, L4, L6]
competency: [data_visualisation, dashboards]
register: [technical, commercial]
strength: strong
numbers: []
evidence: "context/candidate_brief.md, What she can do, Charts and maps for people who are not analysts, and Stack"
interview_exposure: "QGIS will be read as GIS competence by a GIS employer. It is basic. Leave it out unless the posting names it, and say basic when it is in."
```
**short:** D3, Observable Plot, Power BI, Metabase, Figma

**long:** Same, plus "QGIS (basic)" where the posting names GIS or maps.

---

## Not claimed here

- **No cloud data platform in production.** No Azure, AWS, Snowflake, Databricks, Spark or Kafka beyond courses, and courses are not listed as skills. No BigQuery, Redshift or GCP either. If a posting names one as a requirement, that is a gap for `notes.md`.
- **No Kubernetes, Terraform or CI/CD tooling.** Docker, git and Linux are in the stack. Nothing above them is.
- **No Java, C#, .NET, Go or Rust.** Any language or framework not in the short lines above is not listed.
- **No named CMS and no PHP or JavaScript framework from the agency years.** The brief says "a headless CMS" and names no product. Do not write WordPress, Laravel, Vue, Next.js or any other name because a posting mentions it.
- **No accessibility standard, audit or certification.** The brief says "accessibility fixes". Do not write WCAG, a conformance level or "accessibility specialist".
- **No Tableau, Looker or Qlik.** The dashboard tools are Power BI and Metabase.
- **No machine learning and no AI tooling.** No model she trained, no scikit-learn, PyTorch or TensorFlow, no "data science", no language model work. The brief mentions none of it, so no block does. Never write "AI engineer", "AI developer" or "ML".
- **QGIS is basic.** It is never listed without the word.
- **No diary studies, focus groups, surveys, card sorting, thematic analysis, A/B testing or eye tracking.** The methods line is the full set.
- **No testing framework and no SQL dialect beyond PostgreSQL.**
- **No agile, Scrum or project management certification, and no formal project model.** Five years at one small employer.
- **No management skills.** She has never had staff or a budget. Do not list "leadership", "people management" or "budgeting".
- **No "Swedish (native)".** Languages are in `identity.md` and Swedish is her second language.
