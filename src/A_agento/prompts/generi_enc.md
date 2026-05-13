Generate an .enc file for the encik personal knowledge base. Follow the format rules below precisely.

# .enc format rules

## FILE STRUCTURE

```enc
   terminologio.{{lang}} = "term"        # required, one per language
   difino.{{lang}} = "short def"         # single-line definition
   difino.{{lang}} = """               # multi-line definition

   ## one-line summary of the entry at the start of the definition

   - key idea 1
   - key idea 2
   ...

   ## section 1
   
   - point 1.1
   - point 1.2
   ...

   ## section 2
   
   - point 2.1
   - point 2.2

   ...
   """
  semantika="""
  {{type}} {{wikidata-property}} {{value}}
  ...
  """
```

## STYLE for `difino.{{lang}}`

- Include algebraic formula in Katex where relevant (delimiter: $...$)
   - Keep formatting minimal, no extra explanation inside the .enc file
   - **For time, refer to year, not date** -- "1879" not "1879-03-14"
     - exception: for events that repeat every year, like Christmas
   - Use markdown multi-level `-` lists, one idea per point
   - Use inline semantic links to link to any relevant concept that you mention: 
     - format: `[value](#uuid, semantic-property)`
       - which is an alternative in-text form of standard semantic statement: `subject(terminologio) (has)semantic-property value`
     - POSITIVE EXAMPLE: `- Institucio de eduko: [ETH Zurich](#UUID, wdt:P69)`
        - which means the subject (terminologio) was educated (wdt:P69) in ETH Zurich
     - NEGATIVE EXAMPLES:
       - `[Institucio de eduko](#, wdt:P69): ETH Zurich` X
         - the semantic object is ETH Zurich, NOT institucio de eduko
       - `terminologio="Rusio"...difino.eo="...[882](#46a982d2, wdt:P571) :Kieva Regno...` X
         - This inline semantic link suggests that Rusio (terminologio) was founded in 882, which is wrong. 882 is the founding year of Kieva Regno, but NOT modern Russia. The entry's terminologio is about Rusio, so all semantic links must have Rusio as subject. The correct usage here would be simply [882](#46a982d2), without any explicit semantic links, which correctly suggests that "882" is a significant year in Russian history, but NOT directly semantically linked to modern Russia ("Rusio")

## WORKFLOW for creatin inline semantic links in `difino.{{lang}}` (use MCP tools):
- UUID: (compulsory): `search_encik("term")` -- get UUID by title
  - for :
- semantic-property predicate (best endeavour): `wikidata_property_id("keyword")` -- get Wikidata property ID
 - semantic-property predicate should be included where there exists an appropriate semantic arc linking value to semantic subject (terminologio). If the semantic object is only loosely related to the semantic subject (terminologio) so no explicit semantic arc is appropriate, it can be omitted

## STYLE for `semantika`
- syntax inspired by wikidata-flavoured SPARQL
- e.g., `int wdt:P1082 890` signifies that the entry subject has property wdt:P1082 (population) of value of 890
- {{type}}: `int`, `float` `str` or `bool`
  - for int/float, use 4 significant digits, with scientific notation (e.g., `3.0E8`) where appropriate
- {{wikidata-property}}: same as in inline semantic links, use `wikidata_property_id("keyword")` MCP tool to get Wikidata property ID

## TIME ENTRIES (years, decades, centuries)

Years, decades, and centuries are auto-created on first lookup via `search_encik`.
The response includes all three UUIDs so you can reference any of them.

- `search_encik("1879")` → year entry, returns `uuid` (year), `decade_uuid`, `century_uuid`
- `ensure_decade("1780")` → decade entry only, returns `uuid` (decade), `century_uuid`
- `ensure_century("18")` → century entry only, returns `uuid` (century)

Once obtained, use the UUID in inline links or ligilo:
  `[1789](#year-uuid, wdt:P580)` — year as point in time
  `[1780s](#decade-uuid, wdt:P361)` — decade as part of century
  `[18-a jc.](#century-uuid, wdt:P361)` — century as containing decade

Semantika example for year:
```enc
  semantika="""
  str wdt:P580 "1789"
  int wdt:P571 1789
  """
```

## **`semantika` is for numerical values and literal string, whereas `difino` is for explanatory text**
- numerical values like population, land area, etc. should be in `semantika`, not `difino`
- strings where exact wording is important, e.g.: quotes, mottos, should be in `semantika` (use `str`)
- explanatory text, including dates, history, definition of term, etc., should be in `difino`
- `difino` and `semantika` are complementary and should NOT repeat same information twice
  - e.g, if `semantika` includes `str wdt:P1451 "Liberté, Égalité, Fraternité"`, `difino` should NOT remention "Liberté, Égalité, Fraternité". The only exception is that if further explanation is done in `difino` on the republican slogan, and reptition becomes therefore inevitable

## LANGUAGES
- `terminologio` should be in 3 default languages: `eo`, `fr`, `en` + the original language of the concept, IF not among `eo`, `fr`, `en`
  - `e.g.`, for an entry on spain, we would include the 3 default + the local language `es`
- `difino` should be in `eo`

Topic: {prompto}
Generate directly the .enc content. No word padding. No extra explanation.
