# Candidate brief

<!--
DEMO DATA. Maren Kjeldsen does not exist. She was invented for the public copy of jobFinder so
that the pipeline has someone to rank jobs for. Her background, limits and preferences are
made up for the demo. The real system reads a brief of the same kind about its one real
user. Everything inside this comment is stripped before the prompt is sent.
-->

**This is the file the classifier reads to decide whether a job is good for Maren.**
It goes into the cached system prompt on every classification call, so it stays short.

**This is the file to edit when the ranking is wrong.** If good jobs are scoring low, or bad
jobs are scoring high, the fix is almost always here rather than in the prompt. A change
here means a new `classifier_version` and a re-run, so edit it deliberately.

It is never shown to an employer, so it states limits plainly in a way a CV would not. Those
limits are what make the reach rating mean anything: a brief that oversells produces a
classifier that recommends jobs she will not get.

---

## Who

Maren Kjeldsen, 34, lives in Uppsala with her family. Danish citizen, nine years in Sweden.

Bachelor's degree in software development, 2013. Master's in human-computer interaction,
2019, with a thesis on a visualisation tool for household energy data.

Eight years of work. Three as a web developer at an agency. Five at a small energy advice
company in Uppsala, where she is the one developer and analyst: she built its reporting
pipeline, its internal tools and its dashboards, and she is the person the advisers ask
when a number looks wrong.

She is looking because the company is too small to grow in. She wants colleagues in her
own trade and a product more people use.

## What rules a job out

- **Where.** Sweden. A workplace abroad is out unless the role is fully remote. Inside
  Sweden nothing is ruled out by place: see what she wants, below.
- **Language.** She works in Swedish, Danish and English, and reads Norwegian. A job that
  must be done in German, French, Spanish or Dutch is out.
- **Pay.** A post with no pay is out, whatever it is called.
- **Citizenship.** She holds a Danish passport and no other. A post open only to Swedish
  citizens is closed to her, and so is a post in a security class, because the vetting for
  those presumes Swedish citizenship. An ordinary background check is not that.
- **Licences.** She holds no professional licence or authorisation. A post that needs
  legitimation or an equivalent credential is out.
- **Doctorate.** She has none. An ordinary job that requires one is out. A doctoral
  student position does not require one and is judged as its own track.

She has a driving licence.
Pay below about 41,000 SEK a month is a minus and not a bar. Stated pay of 47,000 or more
is a plus.
She wants a permanent post. A fixed term of a year or more is acceptable.

## What she can do

**Data pipelines, end to end.** A nightly pipeline in Python and SQL that collects meter
readings from three suppliers, cleans them and loads them into PostgreSQL. dbt models with
tests on top. Scheduling in Airflow, which she set up and runs.

**Internal tools.** A customer follow-up tool in TypeScript and React used daily by five
advisers. Monthly reports to municipal customers generated from templates. Integrations
between the booking, accounting and customer systems through their APIs.

**Web development.** Three years of client sites and small web applications at an agency:
JavaScript, PHP, a headless CMS, accessibility fixes, handover to customers.

**Design with users.** Interviews, contextual inquiry, moderated usability tests,
prototypes in Figma. Her thesis tool was tested with twelve households, and the work
became a peer-reviewed workshop paper.

**Charts and maps for people who are not analysts.** Dashboards in Power BI and Metabase,
custom charts in D3 and Observable Plot, and a public map of advice visits per district
made for one municipality.

**Stack.** Python, SQL, TypeScript, JavaScript, PHP, HTML and CSS. pandas, dbt, PostgreSQL,
Airflow. React, D3. Power BI, Metabase. Docker, git, Linux. Figma. QGIS at a basic level.

**Languages.** Danish is her first language. Her Swedish is fluent in speech and good in
writing. English is a working language.

## Limits, which set the reach rating

- **She has never had staff or a budget.** She has led work and never people. A post that
  requires personalansvar or experience as a manager is a long reach.
- **Small data, on one server.** No cloud data platform in production: no Azure, AWS,
  Snowflake, Databricks, Spark or Kafka beyond courses. One of them named as a requirement
  is a real gap. A whole job built on them is a long reach.
- **One small employer for five years.** No experience of large organisations, steering
  groups, procurement or formal project models.
- **Swedish is her second language.** A job whose core is writing Swedish for the public,
  such as kommunikatör or redaktör, is a long reach.
- **Level.** Eight years is right for a post asking three to eight. A post asking ten or
  more, or titled principal or head of, is a stretch. A trainee or graduate programme is
  aimed at new graduates and she would not be taken.
- **Teaching.** Two guest seminars and one intern supervised. For a university teaching
  post that is thin.
- **Not a student.** A post that requires current enrolment, such as amanuens, exjobb or a
  student assistant job, cannot go to her.

## What she wants, which sets the want rating

Rate high:

- **Owning a data product from source to screen**: the pipeline, the model and what people
  see.
- Work whose point is public benefit: energy, climate, public transport, open data,
  municipal and regional services.
- Sitting close to the people who use what she builds, and testing with them.
- A team with other developers, analysts or designers in it, small enough that she knows
  everyone.
- Bringing newer colleagues on. She wants to mentor.
- Work in or near Uppsala, or remote. Two or three office days in Stockholm is fine.
  Place is a preference and never a bar: for the right job she would consider another
  Swedish city, so rate an on-site job elsewhere on its work and take a point or two off.
- Danish used in the job.
- Open source, and employers that publish what they build.

Rate low:

- **On-call and shift work.** Jour, beredskap, nights or weekends on a rota. This is her
  clearest no, and no domain makes up for it: an on-call post at a climate company is
  still an on-call post. Rate it 0 to 2.
- **Being hired out.** Consultancies that place her at a customer's office for a year at a
  time. Building for customers from the employer's own office is fine.
- Travel as a regular part of the job.
- A daily commute to Stockholm with no remote days.
- Work that is only keeping a system running, with nothing new built.
- Roles far below her level: first-line support, data entry, trainee programmes. They are
  not repellent, they are a step back. Rate them 1 to 3.

## The university lane

A research engineer or research assistant post in human-computer interaction, information
visualisation or interaction design is work she would enjoy and is qualified for. The same
posts in chemistry, biology, medicine or physics are not her field and rate low.

## The doctoral track

A separate track, not a lane. Funded doctoral positions only.

Her field is human-computer interaction, information visualisation, interaction design and
informatics. She would take a funded doctoral position in it, and her master's and workshop
paper make her a credible applicant. A doctoral position in another science is not hers.
