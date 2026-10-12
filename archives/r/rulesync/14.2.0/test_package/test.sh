#!/bin/sh
# rulesync 14.2.0 consumer test.
#
# Exercises the packaged launcher end to end: version/help surface plus a real
# `init` -> `generate` round trip that must produce a Cursor rule file.
set -eu

rulesync=$1

# 1) version
version=$("$rulesync" --version)
test "$version" = "14.2.0"

# 2) top-level help advertises the tool and its main subcommands
help_output=$("$rulesync" --help 2>&1)
echo "$help_output" | grep -q "Unified AI rules management CLI tool"
echo "$help_output" | grep -q "generate"
echo "$help_output" | grep -q "import"

# 3) subcommand help is reachable through the launcher
gen_help=$("$rulesync" generate --help 2>&1)
echo "$gen_help" | grep -q "Generate configuration files for AI tools"

# 4) OHOS-specific: the shipped launcher must run Node through --jitless
#    (V8 JIT is unavailable / unstable on the OHOS runtime this package targets)
launcher_path=$(command -v "$rulesync" || echo "$rulesync")
head -n 5 "$launcher_path" | grep -q -- "--jitless"

# 5) OHOS-specific: the runtime really is OpenHarmony and the Node runtime the
#    launcher uses is reachable in this environment
platform=$(node --jitless -e 'process.stdout.write(process.platform)')
case "$platform" in
    openharmony|linux) ;;
    *) echo "unexpected runtime platform: $platform" >&2; exit 1 ;;
esac

# 6) real end-to-end: init a project, then generate a Cursor rule
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT INT TERM
cd "$workdir"

"$rulesync" init >/dev/null
test -f rulesync.jsonc
test -f .rulesync/rules/overview.md

"$rulesync" generate -t cursor -f rules >/dev/null
test -s .cursor/rules/overview.mdc
grep -q "Project Overview" .cursor/rules/overview.mdc

echo "rulesync consumer tests passed"
