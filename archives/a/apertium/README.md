# apertium

Apertium machine translation core engine — rule-based MT transfer/tagger
pipeline plus deformatters for txt/html/rtf/odt/latex/mediawiki and more.

The package installs `libapertium` (static) plus the `apertium` driver
script and ~50 `apertium-*` binaries under `bin/` (destxt/retxt,
deshtml/rehtml, tagger, transfer, interchunk/postchunk, gen-modes,
validate-* helpers, etc.).

Built with autotools on OHOS using clang 15 + libc++, linking lttoolbox
(P0 dependency, `>= 3.7.2` per `configure.ac:71`), ICU, libxml2 and
utf8cpp. Build-time tools flex/xmllint/xsltproc come from Conan
tool_requires. `apertium` 3.9.12 is required by language-pair data
packages such as `apertium-mkd-eng` 0.1.3.
