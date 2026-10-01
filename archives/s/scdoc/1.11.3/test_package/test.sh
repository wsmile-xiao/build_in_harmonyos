#!/bin/sh
set -eu

printf 'scdoc(1)\n============\n\n# NAME\n\nconsumer test.\n' > input.scd
scdoc < input.scd > output.1
grep -q '^\.TH "scdoc" "1"' output.1
grep -q 'consumer test' output.1
printf 'scdoc consumer PASS\n'
