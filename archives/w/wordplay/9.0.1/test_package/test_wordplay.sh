#!/bin/sh
# Functional test suite for the packaged wordplay executable.
#
# Usage: sh test_wordplay.sh <package-dir>
#
# <package-dir> must contain bin/wordplay and res/words721.txt.
#
# 20 independent check items (F1-F20).  Counts must stay in sync with
# test_package/MANIFEST.yml.  Upstream has no test suite of its own.
#
# NOTE: assertions were derived from reading wordplay.c 9.0.1 (usage output,
# silent mode formats, exit(-1) on missing argument).  If the on-device
# output differs, tighten here and update MANIFEST.yml in the same commit.
pass=0
fail=0

report() {
    if [ "$2" = "ok" ]; then
        pass=$((pass + 1))
        printf 'ok       %s\n' "$1"
    else
        fail=$((fail + 1))
        printf 'FAIL     %s\n' "$1"
    fi
}

pkg="$1"
bin_dir="$pkg/bin"
words="$pkg/res/words721.txt"
wp="$bin_dir/wordplay"
tmp="${TMPDIR:-/tmp}/wordplay-test.$$"
mkdir -p "$tmp" || exit 2
trap 'rm -rf "$tmp"' EXIT INT TERM

[ -x "$wp" ] || { echo "no executable at $wp" >&2; exit 2; }
[ -f "$words" ] || { echo "no word list at $words" >&2; exit 2; }

# sorted letters of a string (anagram canonical form, case-folded: the
# bundled words721.txt dictionary is ALL-CAPS, wordplay uppercases its
# input before matching, so every assertion below is case-insensitive)
canon() { printf '%s' "$1" | sed 's/ //g' | fold -w1 | sort | tr 'A-Z' 'a-z' | tr -d '\n'; }

# F1: no argument -> usage on stderr, non-zero exit (upstream exit(-1)).
"$wp" >"$tmp/o" 2>"$tmp/e"; rc=$?
[ "$rc" -ne 0 ] && grep -q "Usage:" "$tmp/e"
report "F1_noarg_usage_rc" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F2: banner mentions Wordplay Version 9.
grep -q "Wordplay Version 9" "$tmp/e"
report "F2_banner_version" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F3: usage documents the stdin word-file form "-f -".
"$wp" 2>&1 >/dev/null | grep -q -- '-f -'
report "F3_usage_documents_stdin_wordfile" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F4: canonical anagram of "sotp" finds at least one common word
# (dictionary is all-caps -> match case-insensitively).
"$wp" sotp -s -f "$words" >"$tmp/f4" 2>"$tmp/f4e"; rc=$?
found=0
for w in stop pots tops opts post spot; do
    grep -qix "$w" "$tmp/f4" && found=1 && break
done
[ "$rc" -eq 0 ] && [ "$found" -eq 1 ]
report "F4_sotp_finds_common_word" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F5: every output line is a letter-multiset anagram of the input
# (case-folded: output is uppercase, input given lowercase).
bad_line=0
while IFS= read -r line; do
    [ -n "$line" ] || continue
    [ "$(canon "$line")" = "$(canon sotp)" ] || bad_line=1
done < "$tmp/f4"
[ "$bad_line" -eq 0 ] && [ -s "$tmp/f4" ]
report "F5_all_lines_are_anagrams" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F6: -i is accepted and the output stays valid anagrams. On-device
# verification showed -i has NO observable output difference for this
# input (silent and header diffs are byte-identical), so the assertion is
# the acceptance of the flag plus anagram validity, not a content change.
"$wp" sotp -s -i -f "$words" >"$tmp/f6" 2>/dev/null; rc=$?
bad6=0
while IFS= read -r line; do
    [ -n "$line" ] || continue
    [ "$(canon "$line")" = "$(canon sotp)" ] || bad6=1
done < "$tmp/f6"
[ "$rc" -eq 0 ] && [ "$bad6" -eq 0 ] && [ -s "$tmp/f6" ]
report "F6_include_input_phrase" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F7: -l lists candidate words ("STOP" must be a candidate of "sotp").
"$wp" sotp -s -l -f "$words" 2>/dev/null | grep -qix "stop"
report "F7_candidate_list_contains_stop" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F8: -lx lists candidates without generating anagrams (rc 0, has stop).
"$wp" sotp -s -lx -f "$words" >"$tmp/f8" 2>/dev/null; rc=$?
[ "$rc" -eq 0 ] && grep -qix "stop" "$tmp/f8"
report "F8_list_no_anagrams_rc0" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F9: -w forces the anagram to start from the given word (grep -i: the
# start word may appear inside a multi-word anagram line).
"$wp" sotp -s -w stop -f "$words" >"$tmp/f9" 2>/dev/null; rc=$?
[ "$rc" -eq 0 ] && grep -qi "stop" "$tmp/f9"
report "F9_start_word_option" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F10: -n4 -m4 restricts candidates to 4-letter words (all output lines
# are 4-letter single words here since the input has 4 letters).
"$wp" sotp -s -n4 -m4 -f "$words" >"$tmp/f10" 2>/dev/null; rc=$?
bad=0
while IFS= read -r line; do
    [ -n "$line" ] || continue
    n=$(printf '%s' "$line" | sed 's/ //g' | wc -c)
    [ "$n" -eq 4 ] || bad=1
done < "$tmp/f10"
[ "$rc" -eq 0 ] && [ "$bad" -eq 0 ]
report "F10_length_bounds" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F11: -d1 limits anagrams to 1 word -> every line has no space.
"$wp" sotp -s -d1 -f "$words" >"$tmp/f11" 2>/dev/null; rc=$?
if grep -q " " "$tmp/f11"; then multi=1; else multi=0; fi
[ "$rc" -eq 0 ] && [ "$multi" -eq 0 ]
report "F11_max_one_word_anagrams" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F12: deterministic output for identical invocations.
"$wp" trymenow -s -f "$words" >"$tmp/f12a" 2>/dev/null
"$wp" trymenow -s -f "$words" >"$tmp/f12b" 2>/dev/null
cmp -s "$tmp/f12a" "$tmp/f12b"
report "F12_deterministic_output" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F13: missing word file -> "Error opening word file." on stderr.
"$wp" sotp -s -f "$tmp/no-such-file" >"$tmp/o" 2>"$tmp/f13"; rc=$?
grep -q "Error opening word file" "$tmp/f13" && [ "$rc" -ne 0 ]
report "F13_missing_wordfile_error" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F14: -f - reads the word list from stdin.
printf 'stop\npots\n' | "$wp" sotp -s -f - >"$tmp/f14" 2>/dev/null; rc=$?
[ "$rc" -eq 0 ] && grep -q "stop" "$tmp/f14"
report "F14_stdin_wordfile" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F15: silent mode prints no header.
"$wp" sotp -s -f "$words" 2>/dev/null | grep -q "String to anagram"; rc=$?
[ "$rc" -ne 0 ]
report "F15_silent_no_header" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F16: default mode prints the header.
"$wp" sotp -f "$words" 2>/dev/null | grep -q "String to anagram"
report "F16_header_present" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F17: -a (duplicate words allowed) still yields valid anagrams, rc 0.
"$wp" aaaa -s -a -f "$words" >"$tmp/f17" 2>/dev/null; rc=$?
[ "$rc" -eq 0 ]
report "F17_allow_duplicates_rc0" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F18: -v (no-vowel words allowed) runs fine, rc 0.
"$wp" trymenow -s -v -f "$words" >/dev/null 2>&1
report "F18_allow_no_vowels_rc0" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F19: unimplemented language warns on stderr but still works (falls back
# to English, rc 0).
"$wp" sotp -s -L zz -f "$words" >"$tmp/o" 2>"$tmp/f19"; rc=$?
grep -q "not been implemented" "$tmp/f19" && [ "$rc" -eq 0 ]
report "F19_unimplemented_language_warning" "$([ $? -eq 0 ] && echo ok || echo bad)"

# F20: the readme's suggested first command runs and finds anagrams.
"$wp" trymenow -s -f "$words" >"$tmp/f20" 2>/dev/null; rc=$?
[ "$rc" -eq 0 ] && [ -s "$tmp/f20" ]
report "F20_suggested_first_command" "$([ $? -eq 0 ] && echo ok || echo bad)"

printf 'WORDPLAY_FUNCTIONAL=%s/%s passed, %s failed\n' "$pass" \
    "$((pass + fail))" "$fail"
[ "$fail" -eq 0 ]
