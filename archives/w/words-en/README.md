# words-en

American English word-list data derived from the GNU Aspell English
dictionary release.

The Conan package installs the UTF-8 word list at `share/dict/words-en` and
exposes its absolute path as `WORDS_EN_FILE` in Conan build and run
environments. The package is data-only and has no runtime or build-time Conan
dependencies.

The source is the official GNU Aspell dictionary archive. The package is
licensed under GPL-2.0-or-later. Its American English list is generated from
the common and `en_US` dictionary inputs using the ordering and deduplication
rules of Alpine's `words` package.
