# JobTech field mapping

*Written for the real system, with examples removed. Counts are from its store of real ads,
and lane codes and config keys refer to its configuration, which is not the demo configuration
in this repository.*

**This is the authoritative field mapping for the project.** `posting_schema` in
`02_search_config.yaml` used different field names, about half of them wrong, and it points
here instead of describing fields itself. Two schemas that disagree is how this drifts.

Measured in September 2026 against the live API and a store of about 16,000 ads. Everything in
it came back from the live API or out of `data/postings.db`; nothing is from memory. Re-measure
a section before trusting it a year later.

Endpoints used, all public and unauthenticated, no key and no account:

```
https://taxonomy.api.jobtechdev.se/v1/taxonomy/main/concepts?type=occupation-field
https://jobsearch.api.jobtechdev.se/search?occupation-field=<id>&limit=<n>
https://jobstream.api.jobtechdev.se/stream?date=<ISO8601 UTC>
https://jobsearch.api.jobtechdev.se/swagger.json          # the full parameter list
```

---

## 1. Occupation field concept IDs

All 21. The seven marked **use** are the sweep set for the user's lanes.

| concept ID | label | |
|---|---|---|
| `apaJ_2ja_LuF` | Data/IT | **use**, L1 L2 L3 L4 L7 |
| `X82t_awd_Qyc` | Administration, ekonomi, juridik | **use**, L1 L6 |
| `RPTn_bxG_ExZ` | Försäljning, inköp, marknadsföring | **use**, L1 |
| `MVqp_eS8_kDZ` | Pedagogik | **use**, L5 phd |
| `6Hq3_tKo_V57` | Yrken med teknisk inriktning | **use**, L5 |
| `kJeN_wmw_9wX` | Naturvetenskap | **use**, L5 phd |
| `9puE_nYg_crq` | Kultur, media, design | **use**, L4 L6 L7 |
| `bh3H_Y3h_5eD` | Chefer och verksamhetsledare | |
| `NYW6_mP6_vwf` | Hälso- och sjukvård | |
| `GazW_2TU_kJw` | Yrken med social inriktning | |
| `ASGV_zcE_bWf` | Transport, distribution, lager | |
| `j7Cq_ZJe_GkT` | Bygg och anläggning | |
| `wTEr_CBC_bqh` | Industriell tillverkning | |
| `yhCP_AqT_tns` | Installation, drift, underhåll | |
| `ScKy_FHB_7wT` | Hotell, restaurang, storhushåll | |
| `PaxQ_o1G_wWH` | Hantverk | |
| `VuuL_7CH_adj` | Naturbruk | |
| `E7hm_BLq_fqZ` | Säkerhet och bevakning | |
| `Uuf1_GMh_Uvw` | Kropps- och skönhetsvård | |
| `whao_Q6A_ScE` | Sanering och renhållning | |
| `bH5L_uXD_ZAX` | Militära yrken | |

---

## 2. Volume

Measured over a real 24 hour window.

| | |
|---|---|
| JobStream events, all fields, 24h | 6,906 |
| of those, removals | 4,235 (61 percent) |
| of those, live ads | 2,671 |
| live ads in the seven fields | **966 per day** |
| of those, published within the window | 856 |
| of those, re-emitted updates to older ads | 110 |
| open ads, summing the seven fields' reported totals | 16,088 |
| open ads, **distinct** | **15,483** |

**The 966 is steady state, not a first pass.** JobStream is a change feed, so it already carries
only what is new or changed. The one-time backfill is the distinct open ads, worth about 17 days
of steady-state volume. After the backfill the rate does not fall.

Distribution across the seven, live ads per day: Administration 304, Försäljning 213, Pedagogik
169, Data/IT 128, Teknisk inriktning 113, Naturvetenskap 20, Kultur/media/design 19.

A nightly run agrees with this. One run covering 16h35m applied 588 live ads in the seven
fields, a rate of about 851 a day, consistent with the 966 figure measured over a full window.
Store after that run: 15,979 ads, 15,408 open.

---

## 3. Field mapping

Checked against 15,963 stored payloads.

Left column is what `02_search_config.yaml` used to call it, middle is what the API actually
returns, right is the column in `postings` if it is normalised. `pipeline/normalise.py` is the
implementation and this table is its specification.

| old config name | actual API path | `postings` column |
|---|---|---|
| `job_id` | `id` | `id`, string not int |
| `title` | `headline` | `headline` |
| `occupation` | `occupation.label`, `.concept_id` | `occupation_label`, `occupation_concept_id` |
| - | `occupation_group.label`, `.concept_id` | `occupation_group_label`, `occupation_group_id` |
| `occupation_field` | `occupation_field.label`, `.concept_id` | `occupation_field_label`, `occupation_field_id` |
| `employer_name` | `employer.name` | `employer_name` |
| - | `employer.workplace` | `employer_workplace`, often differs from `.name` |
| `employer_org_number` | `employer.organization_number` | `employer_org_number` |
| - | `employer.url` | `employer_url`, 63 percent |
| `city` | `workplace_address.municipality` | `municipality`. `.city` also exists and is not the same |
| `region` | `workplace_address.region` | `region`, `region_concept_id` |
| `country` | `workplace_address.country` | `country`, `country_code` |
| `latitude`, `longitude` | `workplace_address.coordinates` | `longitude`, `latitude`. **One array, `[lon, lat]`.** See section 6 |
| `employment_type` | `employment_type.label` | `employment_type` |
| - | `duration.label` | `duration`, permanent against fixed term |
| `working_hours_type` | `working_hours_type.label` | `working_hours_type` |
| - | `scope_of_work.min`, `.max` | `scope_min`, `scope_max`, percentage |
| `salary_type` | `salary_type.label` | `salary_type` |
| `salary_description` | `salary_description` | `salary_description`, free text, 0.4 percent |
| `number_of_vacancies` | `number_of_vacancies` | `number_of_vacancies` |
| `must_have_skills` | `must_have.skills` | **not stored.** See section 4 |
| `nice_to_have_skills` | `nice_to_have.skills` | **not stored.** See section 4 |
| - | `must_have.languages[].label` | `must_have_languages`, 13 percent, advisory only |
| - | `experience_required` | `experience_required`. Store it, do not weight it |
| - | `driving_license_required` | `driving_license_required` |
| - | `access_to_own_car` | `access_to_own_car` |
| - | `identified_language` | `identified_language`. JobStream only |
| `description` | `description.text` | **not copied.** Stays in `ads`, see below |
| `application_url` | `application_details.url` | **not stored.** See section 6 |
| - | `webpage_url` | `webpage_url`. The Platsbanken listing, and the dashboard's link out |
| `application_deadline` | `application_deadline` | `application_deadline` |
| `published_at` | `publication_date` | `publication_date` |
| - | `last_publication_date` | `last_publication_date` |
| `last_updated` | `timestamp` | `last_updated`, converted from epoch ms to ISO |
| - | `source_type` | `source_type` |
| - | `removed`, `removed_date` | `removed`, `removed_date`, **from the `ads` column, not the payload** |

**`description.text` is not copied into `postings`.** It is 100 percent populated, median 3,403
characters, 55.5 MB across the store, about 13.9M tokens. Nothing in the dashboard renders it in
full, so it stays in the raw payload in `ads` and the classifier and brief writer read it on
demand. That keeps `postings` small enough to query freely.

**`relevance` appears in JobSearch responses only** and is a per-query score, not a property of
the ad. Do not store it.

**`workplace_addresses` (plural) duplicates `workplace_address`** and is JobSearch only. Not
stored.

---

## 4. Fields that look useful and are not

Measured across the 15,963 stored payloads. A single 24 hour window gives different figures in
two places, noted below.

| field | populated | verdict |
|---|---|---|
| `must_have.skills` | 2.2 percent | Cannot carry matching. The structured skill arrays are almost always empty, so requirements live in `description.text` and nowhere else |
| `nice_to_have.skills` | 4.2 percent | same |
| `must_have.education` | 3.0 percent | same |
| `nice_to_have.work_experiences` | 19.5 percent | The most populated of the structured requirement fields by a wide margin, and still not enough to match on. Nothing in the config maps to it |
| `must_have.languages` | 13.2 percent | Stored, advisory only. Maps to the `language_not_held` hard filter, but at 13 percent it can support a filter and never a search |
| `workplace_model` | **constant** | Useless. See below |
| `experience_required` | true on 94.0 percent | Useless as a discriminator. It does not separate junior from senior, so it must not gate the L3 lane |
| `driving_license_required` | true on 18.1 percent | **Real.** The one high-signal boolean in the set, and it answers the config's open `drivers_licence: unknown` question |

**`workplace_model` is not absent, it is uniform.** JobStream omits the field, so measured on
JobStream it looks 0 percent populated. It is present on 15,364 of 15,963 stored ads, every ad
that arrived through JobSearch, and its value is the constant `Arbete på plats` on all 15,364 of
them. The distinction matters because "absent in the data" invites someone to go and fetch it
from JobSearch and believe they have gained a hybrid or remote signal. They have gained a column
with one value. A hybrid preference cannot be matched on it, and remote against on-site has to
be read out of the description.

**`driving_license_required` depends on the sample.** Over one 24 hour window it is true on 33
percent. Across the whole store it is 18.1 percent. Both are right for what they measured; the
store-wide figure is the one to plan with.

This section is the evidence for the config's own design rule that recall is lost at the query
and never at the ranking. The structured fields are too sparse to filter on, so full ad text and
a model reading it is not a preference, it is the only option.

---

## 5. The search filter is broader than the ad's own field

`?occupation-field=X` does **not** return only ads whose payload says
`occupation_field.concept_id == X`. Summing the seven fields' reported totals gives 16,090, but
those queries return only 15,483 distinct ads: 607 ads come back under two different field
queries, and 85 ads have an `occupation_field` that is not one of the seven at all. They match
on the ad's occupation concepts, not on the single field value the ad reports.

**Consequence, and it is load-bearing.** The store is the candidate set. Selecting ads with
`WHERE occupation_field_id IN (the seven)` silently drops 85 real ads that the sweep
deliberately retrieved. Classify what is in the store; do not re-filter it by field.
`pipeline/normalise.py` has a verification check that fails if those 85 ever stop arriving.

Per-field counts in the store will therefore never match the API's per-field totals, and that is
not a bug. The check that matters is membership: sample ids from the API and confirm they are
present. Of 700 sampled across the seven, none were missing.

---

## 6. Traps

- **`coordinates` is `[longitude, latitude]`.** GeoJSON order, the reverse of how it is usually
  written. Storing it into `lat, lon` columns without swapping puts every job in the wrong
  place. Verified against the data rather than the docs: 3,153 Stockholm ads have median first
  element 18.057 and second 59.334, and Stockholm is longitude 18.07, latitude 59.33.

- **`coordinates` can be `[null, null]`.** 1,449 ads, 9.1 percent. Code that assumes two floats
  either crashes or writes nulls into one column and not the other. `normalise.py` requires both
  elements and has a check that no pair is half populated.

- **A removal never appears in the stored payload.** A JobStream removal is a sparse tombstone,
  nine keys and no description, so `pipeline/store.py` writes it to the `ads.removed` column and
  deliberately leaves the payload alone. The stored payload of a closed ad therefore still says
  `removed: false`. Anything reading removal state must read the column. Reading it from the
  payload reports 0 closed ads where the column has 555.

- **`timestamp` is epoch milliseconds**, while every other date field is an ISO 8601 string.

- **Removals outnumber live ads two to one.** A stream consumer that filters on `removed == false`
  and discards the rest never learns that an ad closed, and the dashboard shows dead postings
  forever.

- **`webpage_url` is not the application link.** It is the Platsbanken listing, always present,
  and it is what the dashboard cards link to because it is the page a human reads.
  `application_details.url` drops straight into the employer's ATS form, is null on 1,695 ads,
  and is not stored: the application is made by hand from the listing.

- **JobStream and JobSearch return different field sets.** JobStream adds `identified_language`
  and omits `relevance`, `workplace_model` and `workplace_addresses`. Write the adapter against
  JobStream, which is the ingestion path.

- **There is no seniority filter in the API.** Checked against the full parameter list in
  `swagger.json`. The only experience parameter is `experience`, which maps to the
  `experience_required` boolean and returns 976 of 16,034 ads, 8 of 2,556 in Data/IT. It is a
  rarely set "no experience whatsoever" flag, not a seniority control. JobStream, the nightly
  path, takes no filters at all beyond `date`. Seniority is filtered between the store and the
  classifier, never at the fetch.

- **JobTech is Sweden only, but not every ad is a job in Sweden.** 99.2 percent of stored ads
  are in Sweden. The other 127 open ads are Swedish-registered employers advertising work abroad,
  mostly Malta, Spain, Greece and Bulgaria through two recruiters, and they are largely
  Danish- or Swedish-speaking customer support. One is a software engineer post in
  another European country, which is a reminder not to reject on
  country before the model has read the ad.
  The `location_out_of_scope` hard filter is what handles these, not the ingestion.

---

## 7. JobAd Links, the other job sites

Read by `pipeline/links.py`.

- **Endpoint.** `https://links.api.jobtechdev.se/joblinks`, version 1.4.5, no key. It takes
  `occupation-field`, `published-after` and `exclude_source`, under the same caps as JobSearch,
  `limit` 100 and `offset` 2000. It has no change feed and is refreshed once a day, so
  `pipeline/links.py` pulls the whole set every run and closes an ad Links stops listing.
- **Most of it is Platsbanken.** 42,448 of 44,208 ads list `arbetsformedlingen.se` among their
  `source_links`, with the Platsbanken ad number in the URL. `exclude_source=arbetsformedlingen.se`
  drops them. 1,443 of 1,520 such numbers were already in `ads`.
- **Fields.** A 32 character hex `id`, `headline`, `brief`, `occupation_group` and
  `occupation_field` as `label` and `concept_id` from the same taxonomy as JobTech, set by Links'
  own classifier, `employer.name`, `workplace_addresses` as a list with the same municipality,
  region and country concept ids, `publication_date`, and `source_links`. No description,
  deadline, salary, employment type or coordinates. 300 of the 1,226 non-Platsbanken ads have no
  address.
- **`brief` is cut on purpose**, median 253 characters. The full text is read from the ad's own
  page; see the readers in `pipeline/links.py`.
- **The mapping into `ads`** is `links.payload_for`: a JobTech-shaped payload with the page's text
  as `description.text`, the first Swedish address as `workplace_address` with `country_code`
  199, the group as `occupation`, the site's page as `webpage_url`, a deadline only where the page
  gives one, and the Links hit kept under `links`. `postings.source` is `links` and
  `postings.source_site` the site.
- **Traps.** Group labels match `context/occupation_groups.md`, so the pre-filter works as it is.
  An address is no proof of country: studentjob.se lists Dutch jobs with no address in Links and
  "SE" on the page, caught by `links.dutch`. A page's `validThrough` says nothing about whether an
  ad is open. The employer is often spelled differently from Platsbanken's for the same job,
  "Exempelköping stad" against "Exempelköping kommun", which is what `links.find_twins` is for.
