#!/usr/bin/env bash
set -eu
package=$1
check="$package/bin/boulder-check"
data="$package/share/boulder/data"
project="$package/share/boulder/harmony-project"
temporary=$(mktemp -d)
trap 'rm -rf -- "$temporary"' EXIT
"$check" --version | grep -F 'Boulder 1.02'
"$check" assets "$data"
"$check" roundtrip "$data" "$temporary/roundtrip.map"
if "$check" assets "$temporary/nonexistent"; then
    echo 'Missing asset directory unexpectedly succeeded' >&2
    exit 1
fi
test -s "$project/entry/libs/arm64-v8a/libboulderhost.so"
test -s "$project/entry/libs/arm64-v8a/libeditorhost.so"
test -s "$project/entry/libs/arm64-v8a/libc++_shared.so"
test -s "$package/licenses/ohos-native-runtime/NOTICE.txt"
test -s "$project/entry/src/main/ets/pages/Editor.ets"
test -s "$project/entry/src/main/resources/rawfile/boulder/title.ogg"
test -s "$package/licenses/license.txt"
echo 'Installed game resources, map roundtrip and native host package checks passed'
