// CV template. Generated .typ files import this.
// Typography: serif body, letterspaced small-caps section rules, generous leading.
// Font stack falls back gracefully if Charter is not installed.

#let serif = ("Charter", "Bitstream Charter", "XCharter", "Georgia", "Palatino", "New Computer Modern")
#let mono = ("Geist Mono", "SF Mono", "Menlo", "DejaVu Sans Mono")

#let rule-heading(body) = {
  v(0.9em)
  block(
    width: 100%,
    stroke: (bottom: 0.4pt + rgb("#000000")),
    inset: (bottom: 3pt),
    text(
      size: 8pt,
      weight: "regular",
      tracking: 1.6pt,
      upper(body),
    ),
  )
  v(0.35em)
}

#let entry(role: "", org: "", dates: "", summary: "", bullets: ()) = {
  block(breakable: false, width: 100%, {
    grid(
      columns: (1fr, auto),
      align: (left, right),
      text(size: 10pt, weight: "bold", role)
        + if org != "" { text(size: 10pt, weight: "regular", ", " + org) },
      text(size: 9pt, style: "italic", dates),
    )
    if summary != "" {
      v(1pt)
      text(size: 9.5pt, summary)
    }
    if bullets.len() > 0 {
      v(1pt)
      set list(marker: [·], indent: 0pt, body-indent: 6pt, spacing: 4pt)
      for b in bullets [
        - #text(size: 9.5pt, b)
      ]
    }
  })
  v(0.5em)
}

#let cv(
  name: "",
  title: "",
  contact: "",
  body,
) = {
  set document(title: name + " CV", author: name)
  set page(
    paper: "a4",
    margin: (x: 18mm, y: 16mm),
  )
  set text(font: serif, size: 10pt, lang: "en", hyphenate: false)
  set par(justify: false, leading: 0.58em, spacing: 0.6em)

  align(center, {
    text(size: 19pt, weight: "regular", tracking: 0.5pt, name)
    if title != "" {
      linebreak()
      v(1pt)
      text(size: 10pt, tracking: 0.8pt, title)
    }
    if contact != "" {
      linebreak()
      v(3pt)
      text(size: 8.5pt, contact)
    }
  })
  v(0.6em)

  body
}
