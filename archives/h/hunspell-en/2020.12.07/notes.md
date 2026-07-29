# hunspell-en 2020.12.07 adaptation notes

The recipe downloads the five immutable dictionaries published by the SCOWL
project: US, Canadian, Australian, British `-ise`, and British `-ize`. It also
installs `en_GB` as a byte-for-byte alias of the `-ise` dictionary.

All release assets were downloaded as real ZIP archives and each SHA-256 was
computed locally. The canonical tagged source is downloaded separately for its
upstream `make test` suite. That suite has two top-level entries:
`scowl_test` (database, dictionary generation, and SQL checks) and
`varcon_test`.

SQLite 3.37 and later reject the suite's unquoted `\t` separator as a
two-character delimiter. Before running the suite, the recipe quotes that
existing escape so it remains one tab on both older and current SQLite; no
test data or assertion is removed.

The added consumer validates every installed dictionary's declared entry
count, UTF-8 affix declaration, dialect-specific spellings, negative lookup,
and missing-directory fault behavior.
