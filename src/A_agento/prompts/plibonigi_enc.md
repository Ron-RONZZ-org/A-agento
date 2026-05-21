Enhance and expand the following .enc entry for the encik personal knowledge base. Read the existing entry carefully, then expand it according to the enhancement instructions. Preserve all existing content and structure; only add or improve sections as instructed.

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

## `difino.{{lang}}`: required, katex+semantic links enhanced markdown with predefined structure

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
         - This inline semantic link suggests that Rusio (terminologio) was founded in 882, which is wrong

### use MCP tools to create inline semantic links in `difino.{{lang}}`

- UUID: (compulsory): `search_encik("term")` -- get UUID by title
  - if not found, try alternative search terms (at most 2 attempts)
  - if still not found after 2 attempts, stop searching and leave blank
- semantic arc (best endeavour): `wikidata_property_id("keyword")` -- get Wikidata property ID
 - semantic arc should be included where there exists an appropriate semantic arc linking value to semantic subject (terminologio)

#### special case: TIME ENTRIES (years, decades, centuries)

- you should always create a inline semantic link when refering to time.
  - UUID: required, will be autocreated if does not yet exist
  - wdt:xxx: optional. can be omitted if there is no appropriate semantic arc found
- MCP tool usage
  - `search_encik("1879")` returns `uuid` (year), `decade_uuid`, `century_uuid`
  - `ensure_decade("1780")` returns `uuid` (decade), `century_uuid`
  - `ensure_century("18")` returns `uuid` (century)

## `semantika`: optional, syntax inspired by wikidata-flavoured SPARQL
- e.g., `int wdt:P1082 890` signifies that the entry subject has property wdt:P1082 of value 890
- {{type}}: `int`, `float` `str` or `bool`
- {{wikidata-property}}: same as in inline semantic links, use `wikidata_property_id("keyword")`

## `semantika` v. `difino`: **`semantika` is for numerical values and literal strings, whereas `difino` is for explanatory text**
- numerical values like population, land area, etc. should be in `semantika`, not `difino`
- strings where exact wording is important, e.g.: quotes, mottos, should be in `semantika` (use `str`)
- explanatory text, including dates, history, definition of term, etc., should be in `difino`
- `difino` and `semantika` are complementary and should NOT repeat same information twice

## LANGUAGES
- `terminologio` should be in 3 default languages: `eo`, `fr`, `en` + the original language of the concept, IF not among `eo`, `fr`, `en`
- `difino` should be in `eo`, EXCEPT if specified otherwise

## CRITICAL: Search limit
You have a maximum of 3 search calls per new entity. After 3 unfruitful searches, stop searching and generate the enhanced entry using your existing knowledge. Omit inline semantic links for entities you couldn't find. If you have searched 5+ times total and still lack data, stop all searching and generate the enhanced entry now with what you know.

{context}
Enhancement instructions: {instruction}

Existing entry to enhance:
{original_text}

Generate the expanded .enc content, preserving all existing content and adding the new content as instructed. No word padding. No extra explanation.
