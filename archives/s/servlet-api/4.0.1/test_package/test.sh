#!/usr/bin/zsh
# test_package/test.sh — Compile and run a servlet-api consumer.
set -euo pipefail

pkg_dir="$1"
java_home="$2"
jar_path="$pkg_dir/libexec/javax.servlet-api-4.0.1.jar"
source_dir="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d "${TMPDIR:-/tmp}/servlet-api-test.XXXXXX")"
trap 'rm -rf "$work"' EXIT

test -x "$java_home/bin/java"
test -x "$java_home/bin/javac"
test -f "$jar_path"
"$java_home/bin/jar" tf "$jar_path" | grep -Fx 'javax/servlet/http/Cookie.class' >/dev/null
"$java_home/bin/jar" tf "$jar_path" | grep -Fx 'javax/servlet/LocalStrings.properties' >/dev/null
"$java_home/bin/javac" -source 8 -target 8 -cp "$jar_path" -d "$work" "$source_dir/TestServletApi.java"
"$java_home/bin/java" -cp "$jar_path:$work" TestServletApi
