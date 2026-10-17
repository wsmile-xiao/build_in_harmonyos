#!/usr/bin/env bash
# test_package/test.sh - 5 offline checks against the packaged kubeconform binary.
# Uses only the local schema in schemas/, no network access.
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-kubeconform>" >&2
    exit 2
fi

kubeconform_bin="$1"
script_dir="$(cd "$(dirname "$0")" && pwd)"
schemas_dir="$script_dir/schemas"
schema_tpl="$schemas_dir/{{.ResourceKind}}{{.KindSuffix}}.json"
valid_yaml="$script_dir/valid.yaml"
invalid_yaml="$script_dir/invalid.yaml"

if [ ! -f "$kubeconform_bin" ]; then
    echo "kubeconform binary not found: $kubeconform_bin" >&2
    exit 1
fi
if [ ! -f "$schemas_dir/testkind-v1.json" ]; then
    echo "local schema missing: $schemas_dir/testkind-v1.json" >&2
    exit 1
fi

# 1. version flag prints the injected version
version_output="$("$kubeconform_bin" -v)"
printf '%s\n' "$version_output" | grep -F "v0.7.0" >/dev/null
echo "CHECK-OK: version flag prints v0.7.0"

# 2. help exits zero
"$kubeconform_bin" -h >/dev/null
echo "CHECK-OK: help exits zero"

# 3. valid manifest validates against the local schema
valid_output="$("$kubeconform_bin" -summary -schema-location "$schema_tpl" "$valid_yaml")"
printf '%s\n' "$valid_output" | grep -F "Valid: 1" >/dev/null
echo "CHECK-OK: valid manifest passes local schema"

# 4. invalid manifest fails with INVALID status (non-zero exit + text proof)
if invalid_output="$("$kubeconform_bin" -summary -schema-location "$schema_tpl" "$invalid_yaml" 2>&1)"; then
    echo "invalid manifest unexpectedly passed" >&2
    exit 1
fi
printf '%s\n' "$invalid_output" | grep -F "Invalid: 1" >/dev/null
echo "CHECK-OK: invalid manifest rejected with Invalid status"

# 5. stdin pipeline validates the valid manifest
stdin_output="$(cat "$valid_yaml" | "$kubeconform_bin" -summary -schema-location "$schema_tpl" -)"
printf '%s\n' "$stdin_output" | grep -F "Valid: 1" >/dev/null
echo "CHECK-OK: stdin manifest validates"

echo "All 5 kubeconform test_package checks passed."
