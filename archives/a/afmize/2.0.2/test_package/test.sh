#!/usr/bin/zsh
# afmize 2.0.2 Conan consumer: run the CLI and verify generated artifacts.
set -euo pipefail
bin="${AFMIZE_BIN:-afmize}"
rm -f afmize-test.ppm afmize-test.tsv afmize-test.json
"$bin" config.toml
for f in afmize-test.ppm afmize-test.tsv afmize-test.json; do
    test -s "$f"
done
