# cdbfasta

cdbfasta/cdbyank are CDB (Constant DataBase) indexing and retrieval tools for
multi-FASTA files: `cdbfasta` builds a `.cidx` index for a FASTA database and
`cdbyank` retrieves records from an indexed database by key.

This archive entry adapts cdbfasta 1.00-git20230710.da8f5ba for OpenHarmony PC
through a Conan package built from the upstream plain Makefile (both CLI tools
installed under `bin/`). Upstream ships no automated test suite; the recipe
exercises the documented index/query workflow and a consumer test drives both
tools.
