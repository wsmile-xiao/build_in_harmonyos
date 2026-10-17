#!/bin/sh
set -eu

test -x "$(command -v xmllint)"
test -x "$(command -v xmlcatalog)"
printf '%s\n' '<root><item>ohos</item></root>' > fixture.xml
xmllint --noout fixture.xml
xmlcatalog --noout /dev/null
rm -f fixture.xml
printf '%s\n' 'libxml2-utils: xmllint/xmlcatalog PASS'
