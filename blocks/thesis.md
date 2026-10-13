<!-- DEMO DATA. Maren Kjeldsen is an invented candidate and every detail in this file is made up. -->

# Thesis, design research and education

The master's thesis, the paper it led to, education and the little teaching there is.
Source: `context/candidate_brief.md`, sections "Who", "What she can do", "Limits, which set
the reach rating" and "The doctoral track".

The thesis has no employer behind it, so for industry postings it goes in Selected projects.
For academic postings and the doctoral track it is the main evidence and leads.

---

## Thesis

### thesis-project
```yaml
type: project
source: thesis
lanes: [L4, L7, L5, phd]
competency: [data_visualisation, interaction_design, usability_testing, user_research]
register: [academic, commercial]
strength: strong
numbers: [12]
evidence: "context/candidate_brief.md, Who, second paragraph, and What she can do, Design with users"
interview_exposure: "What the households misunderstood, and what she changed because of it. This is the question that separates someone who ran a study from someone who lists one. Expect also: how the twelve were recruited, and why work from 2019 is the main design evidence. It is, and the honest answer is that her job since has been building."
```
**short:** Master's thesis: a visualisation tool for household energy data, tested with twelve households.

**long:** Master's thesis in human-computer interaction: a visualisation tool for household energy data, tested with twelve households. The work became a peer-reviewed workshop paper.

---

### thesis-paper
```yaml
type: bullet
source: thesis
lanes: [L5, phd]
competency: [research_methods, academic_writing]
register: [academic]
strength: adequate
numbers: [1]
evidence: "context/candidate_brief.md, What she can do, Design with users, and The doctoral track"
interview_exposure: "A workshop paper is not a full conference or journal paper, and a research group knows the difference. Call it what it is."
```
**short:** The thesis work became one peer-reviewed workshop paper.

**long:** Same. In a Publications section, the full reference goes here once the candidate has added it to this block. Until then use the short variant under the thesis entry.

---

## Education

Typed `skill_term` because a degree is a fixed line, like the contact details. Typed as bullets,
the two would count as evidence for every lane in the index and flatter it.

### edu-master
```yaml
type: skill_term
source: education
lanes: [L1, L2, L3, L4, L5, L6, L7, phd]
competency: []
register: [commercial, technical, academic]
strength: strong
numbers: [2019]
evidence: "context/candidate_brief.md, Who, second paragraph"
interview_exposure: "None for most postings. For a doctoral position: what she has done in the field since 2019. The workshop paper and the visualisation work at her job."
```
**short:** Master's degree in human-computer interaction, 2019. Thesis on a visualisation tool for household energy data.

**long:** Same.

---

### edu-bachelor
```yaml
type: skill_term
source: education
lanes: [L1, L2, L3, L4, L5, L6, L7, phd]
competency: []
register: [commercial, technical, academic]
strength: strong
numbers: [2013]
evidence: "context/candidate_brief.md, Who, second paragraph"
interview_exposure: "None. If a posting requires a named degree title that is not this one, such as civilingenjör, that is a gap for notes.md."
```
**short:** Bachelor's degree in software development, 2013.

**long:** Same.

---

## Teaching

### teaching
```yaml
type: bullet
source: teaching
lanes: [L5]
competency: [teaching]
register: [academic]
strength: thin
numbers: [2, 1]
evidence: "context/candidate_brief.md, Limits, which set the reach rating, Teaching"
interview_exposure: "For a university teaching post this is thin and it is all there is. Do not dress it up."
```
**short:** Gave two guest seminars and supervised one intern.

**long:** Same. Use for L5 postings, where leaving teaching out entirely would read worse than showing how little there is. The intern may also be mentioned where a posting asks about bringing newer colleagues on, as one intern and nothing more.

---

## Not claimed here

- **Not a student.** The master's was finished in 2019. Never write "student", "currently studying" or anything that suggests she is eligible for a post restricted to enrolled students, such as amanuens, exjobb or student assistant.
- **No doctorate.** An ordinary post that requires one is out. A doctoral position is its own track.
- **The degrees are these two and no others.** A bachelor's in software development and a master's in human-computer interaction. Do not rename either to match a posting, and do not write civilingenjör, datavetenskap or "engineering degree".
- **No university named.** The brief names none, so the Education entries carry the degree and the year only. Do not add an institution.
- **No grade, no thesis title, no supervisor, no paper title, venue, year or co-author.** None is in the brief.
- **No technology for the thesis tool.** The brief does not say what it was built with. Do not write D3, React or anything else against it because they are in her stack.
- **No method named for the thesis study beyond "tested with twelve households".** Interviews, contextual inquiry and moderated usability tests are her methods and are listed in `skills.md`. The brief does not say which of them the thesis used, so do not attach them to it.
- **No finding and no result.** The brief does not say what the study showed. No behaviour change, no energy saved, no claim that households understood the tool.
- **No design case from client work.** The agency years were development. The bank holds no UX case, portfolio or client design project, so a UX posting that asks for a portfolio is a gap for `notes.md`.
- **No diary studies, surveys, thematic analysis, A/B tests, eye tracking or statistics.** None appears in the brief.
- **No machine learning.** She has trained no model.
- **No course responsibility, no examination, no course development, no staff responsibility.** Two guest seminars and one intern. Supervising one intern is not managing people.
- **No research employment.** The paper came from the thesis. She has not worked at a university or in a research group.
- **Academic writing in Swedish is not claimed.** Swedish is her second language, good in writing. The brief does not say what language the thesis or the paper is in.
