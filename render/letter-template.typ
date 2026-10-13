// Letter template. Generated .typ files import this.
// Plain letterhead matching cv-template.typ: same typeface, same margins,
// same leading. No headings, no section rules, no logo.

#let serif = ("Charter", "Bitstream Charter", "XCharter", "Georgia", "Palatino", "New Computer Modern")

#let para(body) = {
  block(width: 100%, text(size: 10pt, body))
  v(0.5em)
}

#let letter(
  name: "",
  contact: "",
  recipient: "",
  date: "",
  lang: "en",
  body,
) = {
  set document(title: name + " letter", author: name)
  set page(
    paper: "a4",
    margin: (x: 18mm, y: 16mm),
  )
  set text(font: serif, size: 10pt, lang: lang, hyphenate: false)
  set par(justify: false, leading: 0.58em, spacing: 0.6em)

  align(center, {
    text(size: 19pt, weight: "regular", tracking: 0.5pt, name)
    if contact != "" {
      linebreak()
      v(3pt)
      text(size: 8.5pt, contact)
    }
  })
  v(1.8em)

  if recipient != "" or date != "" {
    if recipient != "" { text(size: 9pt, recipient) }
    if recipient != "" and date != "" { linebreak() }
    if date != "" { text(size: 9pt, date) }
    v(1.4em)
  }

  body
}
