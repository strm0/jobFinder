# Occupation groups: the skip list that runs before the model

The verdicts in the table below are the ones the real system uses. Each group was reviewed
by hand. The file is hand-maintained and `pipeline/prefilter.py` reads it directly, so there
is one copy of the list.

## What this is for

Every JobTech ad arrives carrying an `occupation_group` label, assigned upstream by
Arbetsförmedlingen. It is filled on every ad and drawn from a fixed list. This file decides
which of those groups are worth sending to the model. 96 of the 159 are skipped.

An ad whose group is marked `skip` does not reach the classifier **unless the headline rescue
below returns it**. The group verdict itself involves no text analysis and no model judgement:
it is a lookup on a field that is already there, so it cannot misfire on wording. The rescue is
the one text rule layered on top, and it only ever adds ads back.

## The headline rescue

**A group verdict of `skip` is not final.** An ad in a skipped group is still sent to the model
if its headline names one of the lanes. The terms are in `02_search_config.yaml` under
`prefilter.headline_rescue`, which is the machine-readable source of truth; this section
explains why it exists.

The upstream label is often wrong. A trainee AI consultant filed under Telefonförsäljare, a
senior data scientist under Banktjänstemän, a software developer at a farming startup under
Ingenjörer, maskinteknik: the group rule alone throws all of them away. In the sample data an
AI developer filed under Företagssäljare and an amanuens post filed under Elevassistenter come
back this way.

**A narrow veto stops it becoming a backdoor.** `säljare`, `säljande`, `provision`,
`mötesbokare` and the teaching words override any rescue term, which is what keeps a seller
of AI products and a programming tutor out.

**It is a recall rule, not a precision rule.** A wrongly rescued ad costs a fraction of a cent
and the model rejects it, so the term list is deliberately generous and the veto deliberately
narrow. Do not tune it for precision.

**Its limit is real.** It reads headlines only. An ad whose headline gives nothing away, sitting
in a skipped group, is still lost. Reading descriptions is the cost the pre-filter exists to
avoid.

## How to edit it

Change the word in the **verdict** column and nothing else, then run
`python -m pipeline.prefilter rebuild`. `keep` sends the group to the model, `skip` does not.
The rebuild is free. Its checks include the 96, 63 and 159 counts, so an edit here shows up as
a failed check until that check is updated to match, on purpose.

Skipped ads are not deleted. They keep their reason in the `prefilter` table, so a wrong call
here is visible rather than silent.

**A group missing from the table defaults to `keep`, never `skip`.** New occupation groups turn
up as the taxonomy gets used. The pre-filter fails open and reports anything it did not
recognise with `python -m pipeline.prefilter unknown`, so a new group costs a fraction of a
cent per ad rather than disappearing silently. The sample data has one such ad.

## Two things that shaped the verdicts

**When in doubt, keep.** A wrongly kept ad costs a fraction of a cent and the model rejects it.
A wrongly skipped ad is one you never see. The two errors are not the same size.

**The upstream label is worst on the small groups.** The large groups are clean; the small
ones hold mislabelled ads more often, so small groups default to `keep` unless the field is
plainly out of scope.

## The groups

The first column is how many of the sample ads carry the group, not a count from the real
store.

| sample ads | occupation group | mostly from | verdict |
|---:|---|---|---|
| 10 | Företagssäljare | Försäljning | `skip` |
| 24 | Mjukvaru- och systemutvecklare m.fl. | Data/IT | `keep` |
| 7 | Grundskollärare | Pedagogik | `skip` |
| 6 | Ingenjörer och tekniker inom maskinteknik | Teknisk | `skip` |
| 6 | Butikssäljare, fackhandel | Försäljning | `skip` |
| 1 | Ingenjörer och tekniker inom elektroteknik | Teknisk | `keep` |
| 5 | Kundtjänstpersonal | Administration | `skip` |
| 5 | Butikssäljare, dagligvaror | Försäljning | `skip` |
| 3 | Lednings- och organisationsutvecklare | Administration | `keep` |
| 1 | Civilingenjörsyrken inom elektroteknik | Teknisk | `keep` |
| 4 | Personal- och HR-specialister | Administration | `skip` |
| 6 | Systemanalytiker och IT-arkitekter m.fl. | Data/IT | `keep` |
| 2 | Planerare och utredare m.fl. | Administration | `keep` |
| 5 | Telefonförsäljare m.fl. | Försäljning | `skip` |
| 4 | Civilingenjörsyrken inom maskinteknik | Teknisk | `skip` |
| 4 | Övriga kontorsassistenter och sekreterare | Administration | `skip` |
| 1 | Inköpare och upphandlare | Försäljning | `keep` |
| 3 | Arbetsförmedlare | Administration | `skip` |
| 3 | Redovisningsekonomer | Administration | `skip` |
| 3 | Övriga förmedlare | Försäljning | `skip` |
| 4 | Elevassistenter m.fl. | Pedagogik | `skip` |
| 1 | Idrottstränare och instruktörer m.fl. | Pedagogik | `skip` |
| 1 | Controller | Administration | `skip` |
| 1 | Eventsäljare och butiksdemonstratörer m.fl. | Försäljning | `keep` |
| 1 | Barnskötare | Pedagogik | `skip` |
| 1 | Gymnasielärare | Pedagogik | `skip` |
| 2 | Marknadsanalytiker och marknadsförare m.fl. | Försäljning | `keep` |
| 1 | Drifttekniker, IT | Data/IT | `keep` |
| 1 | Speciallärare och specialpedagoger m.fl. | Pedagogik | `skip` |
| 1 | Supporttekniker, IT | Data/IT | `keep` |
| 3 | Systemförvaltare m.fl. | Data/IT | `keep` |
| 1 | Förskollärare | Pedagogik | `skip` |
| 1 | IT-säkerhetsspecialister | Data/IT | `keep` |
| 1 | Systemtestare och testledare | Data/IT | `keep` |
| 1 | Kontorsreceptionister | Administration | `skip` |
| 1 | Fritidspedagoger | Pedagogik | `skip` |
| 1 | Löne- och personaladministratörer | Administration | `skip` |
| 1 | Ingenjörer och tekniker inom industri, logistik och produktionsplanering | Teknisk | `keep` |
| 2 | Informatörer, kommunikatörer och PR-specialister | Administration | `keep` |
| 1 | Övriga utbildare och instruktörer | Pedagogik | `skip` |
| 1 | Ekonomiassistenter m.fl. | Administration | `skip` |
| 6 | Övriga IT-specialister | Data/IT | `keep` |
| 1 | Övriga handläggare | Administration | `keep` |
| 6 | Doktorander | Pedagogik | `keep` |
| 1 | Systemadministratörer | Data/IT | `keep` |
| 1 | Nätverks- och systemtekniker m.fl. | Data/IT | `keep` |
| 1 | Bibliotekarier och arkivarier | Kultur | `keep` |
| 1 | Säljande butikschefer och avdelningschefer i butik | Försäljning | `skip` |
| 1 | Övriga civilingenjörsyrken | Teknisk | `keep` |
| 1 | Universitets- och högskolelektorer | Pedagogik | `keep` |
| 2 | Forskarassistenter m.fl. | Pedagogik | `keep` |
| 1 | Lärare i yrkesämnen | Pedagogik | `skip` |
| 1 | Civilingenjörsyrken inom logistik och produktionsplanering | Teknisk | `keep` |
| 1 | Övriga pedagoger med teoretisk specialistkompetens | Pedagogik | `skip` |
| 1 | Medicinska sekreterare, vårdadministratörer m.fl. | Administration | `skip` |
| 1 | Fastighetsförvaltare | Teknisk | `skip` |
| 1 | Ordersamordnare m.fl. | Försäljning | `skip` |
| 1 | Affärs- och företagsjurister | Administration | `skip` |
| 1 | Förvaltnings- och organisationsjurister | Administration | `skip` |
| 1 | Trafiklärare | Pedagogik | `skip` |
| 1 | Biomedicinska analytiker m.fl. | Naturvet | `keep` |
| 1 | Speditörer och transportmäklare | Försäljning | `skip` |
| 1 | Ingenjörer och tekniker inom kemi och kemiteknik | Teknisk | `skip` |
| 1 | Specialister inom miljöskydd och miljöteknik | Naturvet | `keep` |
| 1 | Skadereglerare och värderare | Administration | `skip` |
| 1 | Marknads- och försäljningsassistenter | Försäljning | `keep` |
| 0 | Ingenjörer och tekniker inom gruvteknik och metallurgi | Teknisk | `keep` |
| 1 | Miljö- och hälsoskyddsinspektörer | Naturvet | `keep` |
| 1 | Studie- och yrkesvägledare | Pedagogik | `skip` |
| 1 | Finansanalytiker och investeringsrådgivare m.fl. | Administration | `skip` |
| 1 | Kassapersonal m.fl. | Försäljning | `skip` |
| 1 | Fastighetsmäklare | Försäljning | `skip` |
| 1 | Banktjänstemän | Administration | `skip` |
| 1 | Gruppledare för kontorspersonal | Administration | `skip` |
| 1 | Övriga ingenjörer och tekniker | Teknisk | `keep` |
| 1 | Cell- och molekylärbiologer m.fl. | Naturvet | `skip` |
| 0 | Marknadsundersökare och intervjuare | Försäljning | `keep` |
| 1 | Backofficepersonal m.fl. | Administration | `keep` |
| 1 | Laboratorieingenjörer | Teknisk | `skip` |
| 1 | Revisorer m.fl. | Administration | `skip` |
| 1 | Bensinstationspersonal | Försäljning | `skip` |
| 1 | Civilingenjörsyrken inom kemi och kemiteknik | Teknisk | `skip` |
| 1 | Musiker, sångare och kompositörer | Kultur | `skip` |
| 0 | Ljus-, ljud- och scentekniker | Kultur | `keep` |
| 1 | Civilingenjörsyrken inom gruvteknik och metallurgi | Teknisk | `skip` |
| 0 | Fotografer | Kultur | `keep` |
| 1 | Övriga jurister | Administration | `skip` |
| 1 | Kemister | Naturvet | `skip` |
| 1 | Designer inom spel och digitala medier | Kultur | `keep` |
| 0 | Inspicienter och scriptor m.fl. | Kultur | `keep` |
| 1 | Socialförsäkringshandläggare | Administration | `skip` |
| 1 | Journalister m.fl. | Kultur | `keep` |
| 1 | Säkerhetsinspektörer m.fl. | Säkerhet och bevakning | `keep` |
| 1 | Uthyrare | Försäljning | `skip` |
| 2 | GIS- och kartingenjörer | Teknisk | `keep` |
| 1 | Produktionschefer inom tillverkning | Chefer och verksamhetsledare | `skip` |
| 1 | Fysiker och astronomer | Naturvet | `skip` |
| 0 | Elektronikreparatörer och kommunikationselektriker m.fl. | Installation, drift, underhåll | `keep` |
| 0 | Professorer | Pedagogik | `keep` |
| 1 | Farmakologer och biomedicinare | Naturvet | `skip` |
| 1 | Övriga ekonomer | Administration | `skip` |
| 1 | Försäkringssäljare och försäkringsrådgivare | Administration | `skip` |
| 1 | Inredare, dekoratörer och scenografer m.fl. | Kultur | `skip` |
| 0 | Översättare, tolkar och lingvister m.fl. | Kultur | `keep` |
| 1 | Domstols- och juristsekreterare m.fl. | Administration | `skip` |
| 1 | Lantmätare | Administration | `skip` |
| 0 | Arkeologer och specialister inom humaniora m.m. | Administration | `keep` |
| 1 | Guider och reseledare | Försäljning | `skip` |
| 2 | Övriga universitets- och högskolelärare | Pedagogik | `keep` |
| 1 | Tandtekniker och ortopedingenjörer m.fl. | Teknisk | `skip` |
| 1 | Statistiker | Administration | `keep` |
| 0 | Inköps- och orderassistenter | Försäljning | `keep` |
| 1 | Torg- och marknadsförsäljare m.fl. | Försäljning | `skip` |
| 0 | Regissörer och producenter av film, teater m.m. | Kultur | `keep` |
| 0 | Övriga yrken inom kultur och underhållning | Kultur | `keep` |
| 0 | Bild- och sändningstekniker | Kultur | `keep` |
| 1 | Chefssekreterare och VD-assistenter m.fl. | Administration | `skip` |
| 1 | Inkasserare och pantlånare m.fl. | Administration | `skip` |
| 1 | Apotekstekniker | Försäljning | `skip` |
| 1 | Skolassistenter m.fl. | Administration | `skip` |
| 1 | Nationalekonomer och makroanalytiker m.fl. | Administration | `skip` |
| 1 | Resesäljare och trafikassistenter m.fl. | Försäljning | `skip` |
| 1 | Museiintendenter m.fl. | Kultur | `keep` |
| 0 | Arkiv- och biblioteksassistenter m.fl. | Administration | `keep` |
| 1 | Arkitekter m.fl. | Teknisk | `skip` |
| 0 | Övriga designer och formgivare | Kultur | `keep` |
| 1 | Webbmaster och webbadministratörer | Data/IT | `keep` |
| 1 | Åklagare | Administration | `skip` |
| 1 | Geologer och geofysiker m.fl. | Naturvet | `skip` |
| 1 | Domare | Administration | `skip` |
| 1 | Flygtekniker | Teknisk | `skip` |
| 1 | Växt- och djurbiologer | Naturvet | `skip` |
| 1 | Övriga skönhets- och kroppsterapeuter | Kropps- och skönhetsvård | `skip` |
| 1 | Skattehandläggare | Administration | `skip` |
| 0 | Tekniker, bilddiagnostik och medicinteknisk utrustning | Teknisk | `keep` |
| 0 | Industridesigner | Kultur | `keep` |
| 1 | Utvecklare inom spel och digitala media | Data/IT | `keep` |
| 1 | Planeringsarkitekter m.fl. | Teknisk | `skip` |
| 1 | Optikerassistenter | Försäljning | `skip` |
| 1 | Matematiker och aktuarier | Naturvet | `skip` |
| 1 | Traders och fondförvaltare | Administration | `skip` |
| 1 | Telefonister | Administration | `skip` |
| 0 | Evenemangs- och reseproducenter m.fl. | Försäljning | `keep` |
| 0 | Advokater | Administration | `skip` |
| 1 | Grafiska formgivare m.fl. | Kultur | `keep` |
| 0 | Behandlingsassistenter och socialpedagoger m.fl. | Yrken med social inriktning | `skip` |
| 0 | Bildkonstnärer m.fl. | Kultur | `skip` |
| 0 | Övriga specialistsjuksköterskor | Hälso- och sjukvård | `skip` |
| 1 | Transportledare och transportsamordnare | Transport, distribution, lager | `keep` |
| 0 | Landskapsarkitekter | Teknisk | `skip` |
| 0 | Författare m.fl. | Kultur | `skip` |
| 0 | Croupierer och oddssättare m.fl. | Hotell, restaurang, storhushåll | `skip` |
| 0 | Kuratorer | Yrken med social inriktning | `keep` |
| 0 | Chefer inom friskvård, sport och fritid | Chefer och verksamhetsledare | `skip` |
| 0 | Finmekaniker | Hantverk | `skip` |
| 0 | Skådespelare | Kultur | `skip` |
| 0 | Prepresstekniker | Industriell tillverkning | `skip` |
| 0 | Koreografer och dansare | Kultur | `skip` |
| 0 | Meteorologer | Naturvet | `keep` |
