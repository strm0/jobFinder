<!-- DEMO DATA. Maren Kjeldsen is an invented candidate and every detail in this file is made up. -->

# Public map and custom charts

The visualisation work that is not a dashboard. Source: `context/candidate_brief.md`, section
"What she can do", paragraph "Charts and maps for people who are not analysts".

The brief says the map was made for one municipality. It does not say whether it was made at
the energy advice company, so it is placed in Selected projects and never under the employer.
If the candidate confirms it was made at work, change `source` to `energy_advice` and make it
a bullet. The same goes for the custom charts.

---

### district-map-project
```yaml
type: project
source: district_map
lanes: [L7, L6]
competency: [data_visualisation, public_communication, maps]
register: [commercial, academic]
strength: adequate
numbers: [1]
evidence: "context/candidate_brief.md, What she can do, Charts and maps for people who are not analysts"
interview_exposure: "Can I see it. No link is in the bank, so the candidate must have one ready or say why not. Expect: how small districts were handled so that a visit could not be traced to a household, and what it was built with."
```
**short:** A public map of energy advice visits per district, made for one municipality.

**long:** A public map of energy advice visits per district, made for one municipality and meant for readers who are not analysts.

---

### charts-custom
```yaml
type: bullet
source: charts
lanes: [L7, L3, L4]
competency: [data_visualisation, frontend, javascript]
register: [technical, commercial]
strength: adequate
numbers: []
evidence: "context/candidate_brief.md, What she can do, Charts and maps for people who are not analysts"
interview_exposure: "Show one. When does she reach for D3 and when for Observable Plot. An opinion here is worth more than a list of chart types."
```
**short:** Builds custom charts in D3 and Observable Plot for readers who are not analysts.

**long:** Same.

---

## Not claimed here

- **No GIS specialism.** QGIS at a basic level only. Never write "GIS developer", "spatial analysis" or "geodata expert". A GIS posting that requires ArcGIS, FME or PostGIS is a gap for `notes.md`.
- **No technology for the map.** The brief does not say what it was built with. Do not write D3, QGIS or anything else against it.
- **No municipality named, no link, no visitor numbers, no year.**
- **No claim about who paid for the map or under which employer it was made.** "Made for one municipality" is the wording.
- **No commissions and no side business.** The brief mentions no work outside her two jobs. Do not write that charts were made for clients of her own.
- **No procurement or public sector employment.** A map made for a municipality is not experience of working inside one, or of a public procurement.
- **No published text.** The map is public. Writing Swedish for the public is not claimed, and Swedish is her second language.
- **No data journalism.** She has not worked for a newsroom or published under a byline.
- **No design system, brand or illustration work.**
- **No number of charts and no named reader or customer for them.**
