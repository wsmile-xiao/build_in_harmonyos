#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
jar="$script_dir/jflex-full-1.9.1.jar"

if test ! -f "$jar"; then
  echo "jflex: packaged JAR not found: $jar" >&2
  exit 1
fi

if test -n "${JAVA_HOME:-}" && test -f "$JAVA_HOME/bin/java"; then
  java_bin="$JAVA_HOME/bin/java"
elif command -v java >/dev/null 2>&1; then
  java_bin=$(command -v java)
else
  echo "jflex: Java 11 or newer is required" >&2
  exit 127
fi

# HarmonyOS may reject direct execution of packaged shell scripts. Consumers
# invoke this entry point as: sh "$JFLEX_COMMAND" <options> <grammar.flex>
exec "$java_bin" -jar "$jar" "$@"
