#!/system/bin/sh
# letta-code 0.28.17 — consumer checks (driven by test_package/conanfile.py
# under the conanrun environment).
#
# Every assertion runs the packaged CLI for real: the banner comes from
# `letta --version`, and the whole CLI surface below is read out of the real
# `letta --help` output (section by section, not from a copied string).
#
# 53 assertions:
#   1  exact upstream version banner
#   3  help section headers (USAGE / OPTIONS / SUBCOMMANDS)
#   21 USAGE command lines
#   27 SUBCOMMANDS entries
#   1  assertion-count self-check
set -eu

letta_bin="$(command -v letta)"
test -n "$letta_bin"
if [ -x /system/bin/sh ]; then
    launcher_shell=/system/bin/sh
else
    launcher_shell=/bin/sh
fi

work_dir="$(pwd)"
help_file="$work_dir/.letta-help.txt"
usage_file="$work_dir/.letta-usage.txt"
subcommands_file="$work_dir/.letta-subcommands.txt"
expected_usage="$work_dir/.letta-expected-usage.txt"
expected_subcommands="$work_dir/.letta-expected-subcommands.txt"
trap 'rm -f "$help_file" "$usage_file" "$subcommands_file" "$expected_usage" "$expected_subcommands"' 0

assertions=0

# ── 1. exact upstream version banner ───────────────────────────────────────
version_output="$("$launcher_shell" "$letta_bin" --version 2>&1)"
printf '%s\n' "$version_output"
test "$version_output" = "0.28.17 (Letta Code)"
assertions=$((assertions + 1))

# ── 2. real help output, split into its sections ───────────────────────────
"$launcher_shell" "$letta_bin" --help >"$help_file" 2>&1
sed -n '/^USAGE/,/^OPTIONS/p' "$help_file" >"$usage_file"
sed -n '/^SUBCOMMANDS/,/^BEHAVIOR/p' "$help_file" >"$subcommands_file"

for header in USAGE OPTIONS SUBCOMMANDS; do
    grep -F "$header" "$help_file" >/dev/null
    assertions=$((assertions + 1))
done

check_section() {
    list_file="$1"
    section_file="$2"
    section_name="$3"
    while IFS= read -r pattern; do
        [ -n "$pattern" ] || continue
        if ! grep -F -- "$pattern" "$section_file" >/dev/null; then
            echo "MISSING from $section_name: $pattern" >&2
            exit 1
        fi
        assertions=$((assertions + 1))
    done <"$list_file"
}

# ── 3. USAGE command lines (21) ────────────────────────────────────────────
cat >"$expected_usage" <<'EXPECTED_USAGE'
letta --new
letta --resume
letta --new-agent
letta --agent <id>
letta -p "..."
letta update
letta upgrade
letta --update
letta --upgrade
letta memory ...
letta agents ...
letta environments ...
letta messages ...
letta mods ...
letta server ...
letta connect ...
letta backend ...
letta setup
letta install ...
letta skills ...
Resume last conversation for this project
EXPECTED_USAGE
check_section "$expected_usage" "$usage_file" "USAGE"

# ── 4. SUBCOMMANDS entries (27) ────────────────────────────────────────────
cat >"$expected_subcommands" <<'EXPECTED_SUBCOMMANDS'
letta memory status
letta memory diff
letta memory resolve
letta memory backup
letta memory backups
letta memory restore
letta memory export
letta memory pull
letta memory tokens
letta agents list
letta environments list
letta environments current
letta messages search
letta messages list
letta messages transcript
letta mods list
letta mods package
letta mods enable
letta mods disable
letta mods remove
letta server
letta connect
letta install
letta skills list
letta skills delete
letta backend
letta local-backend migrate-transcripts
EXPECTED_SUBCOMMANDS
check_section "$expected_subcommands" "$subcommands_file" "SUBCOMMANDS"

# ── 5. self-check: no assertion may be silently lost ──────────────────────
test "$assertions" -eq 52
assertions=$((assertions + 1))

echo "letta-code 0.28.17 consumer checks: PASS (assertions=$assertions)"
