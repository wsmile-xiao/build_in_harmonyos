#!/usr/bin/env bash
set -eu
version_output="$(acmed --version)"
printf '%s\n' "$version_output"
printf '%s\n' "$version_output" | grep -Eiq '(^|[[:space:]])acmed([[:space:]]|$)'
printf '%s\n' "$version_output" | grep -q '0.25.0'

cat > invalid.toml <<'EOF'
this is not valid TOML
EOF

if acmed --foreground --no-pid-file --log-stderr --config invalid.toml > config.log 2>&1; then
    echo "acmed accepted an invalid TOML configuration" >&2
    exit 1
fi
grep -Eiq 'toml|parse|invalid' config.log
