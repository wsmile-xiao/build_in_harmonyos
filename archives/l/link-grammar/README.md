# Link Grammar

Link Grammar is a natural-language parser that represents syntax as links
between words. The package contains the C/C++ library, language dictionaries,
and the `link-parser` command-line program.

## OHOS adaptation

- The upstream Git tag archive contains Autotools inputs but no generated
  `configure` script. The recipe bootstraps it with the published
  `automake/1.18` and `libtool/2.5.4` tool packages.
- PCRE2 is the required UTF-8 regular-expression implementation.
- SQLite3-backed dictionaries are enabled.
- PCRE2 and SQLite3 static archives are staged in a build-private directory
  without non-relocatable Libtool `.la` metadata. This prevents stale install
  paths and nested dependency archives without mutating the Conan cache.
- Hunspell, Aspell, Editline, SAT, Java, Python, and Perl integrations are
  disabled because their optional dependencies are not part of this package.
- The library and parser are built statically to avoid runtime library search
  paths on HarmonyOS PC.

## Data files

Dictionary data is installed in `share/link-grammar`. Library consumers can
locate it through Conan's `resdirs` metadata and pass the directory to
`dictionary_set_data_dir()` before creating a dictionary.

## References

- Website: https://opencog.github.io/link-grammar-website/
- Source: https://github.com/opencog/link-grammar
