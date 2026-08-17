#!/bin/sh
set -euo pipefail

java_bin=$1
javac_bin=$2
source_dir=$3
work_dir=$4

simple_generated="$work_dir/generated/simple"
simple_classes="$work_dir/classes/simple"
unicode_generated="$work_dir/generated/unicode"
unicode_classes="$work_dir/classes/unicode"
version_log="$work_dir/jflex-version.log"
mkdir -p \
  "$simple_generated" \
  "$simple_classes" \
  "$unicode_generated" \
  "$unicode_classes"

passed=0
failed=0
jflex_jar=${JFLEX_JAR:-}
jflex_command=${JFLEX_COMMAND:-}

if test -n "$jflex_jar" && test -f "$jflex_jar"; then
  passed=$((passed + 1))
else
  failed=$((failed + 1))
  echo "JFLEX_JAR is missing or invalid: $jflex_jar" >&2
fi

if test -n "$jflex_command" && test -f "$jflex_command"; then
  passed=$((passed + 1))
else
  failed=$((failed + 1))
  echo "JFLEX_COMMAND is missing or invalid: $jflex_command" >&2
fi

if sh "$jflex_command" --version >"$version_log" 2>&1 \
    && grep -F "1.9.1" "$version_log" >/dev/null 2>&1; then
    passed=$((passed + 1))
else
    failed=$((failed + 1))
    test ! -f "$version_log" || cat "$version_log" >&2
fi

if sh "$jflex_command" \
    --encoding UTF-8 \
    -d "$simple_generated" \
    "$source_dir/Lexer.flex" \
    && test -s "$simple_generated/GeneratedLexer.java"; then
    passed=$((passed + 1))
else
    failed=$((failed + 1))
fi

if "$javac_bin" \
    -encoding UTF-8 \
    -d "$simple_classes" \
    "$simple_generated/GeneratedLexer.java" \
    "$source_dir/TestLexer.java" \
    && test -s "$simple_classes/TestLexer.class"; then
    passed=$((passed + 1))
else
    failed=$((failed + 1))
fi

if "$java_bin" -cp "$simple_classes" TestLexer; then
    # TestLexer contains five independent semantic assertions.
    passed=$((passed + 5))
else
    failed=$((failed + 5))
fi

if sh "$jflex_command" \
    --encoding UTF-8 \
    -d "$unicode_generated" \
    "$source_dir/UnicodeStateLexer.flex" \
    && test -s "$unicode_generated/UnicodeStateLexer.java"; then
    passed=$((passed + 1))
else
    failed=$((failed + 1))
fi

if "$javac_bin" \
    -encoding UTF-8 \
    -d "$unicode_classes" \
    "$unicode_generated/UnicodeStateLexer.java" \
    "$source_dir/TestUnicodeStateLexer.java" \
    && test -s "$unicode_classes/TestUnicodeStateLexer.class"; then
    passed=$((passed + 1))
else
    failed=$((failed + 1))
fi

if "$java_bin" -cp "$unicode_classes" TestUnicodeStateLexer; then
    # TestUnicodeStateLexer contains seven independent semantic assertions.
    passed=$((passed + 7))
else
    failed=$((failed + 7))
fi

if test "$failed" -eq 0; then
    printf '%s\n' \
      "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"tool_requires env + two jflex grammars + javac + java\",\"discovered\":19,\"passedCount\":$passed}"
    exit 0
fi

printf '%s\n' \
  "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"tool_requires env + two jflex grammars + javac + java\",\"discovered\":19,\"passedCount\":$passed}"
exit 1
