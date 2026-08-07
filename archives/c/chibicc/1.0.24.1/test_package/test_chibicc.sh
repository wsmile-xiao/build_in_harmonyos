#!/usr/bin/env sh
set -eu

: "${CHIBICC_BIN:?CHIBICC_BIN is required}"

workdir="${PWD}/chibicc-smoke"
rm -rf "${workdir}"
mkdir -p "${workdir}/tmp"
export TMPDIR="${workdir}/tmp"
export TMPPREFIX="${workdir}/tmp/sh"

{
  printf '%s\n' 'int add(int a, int b) {'
  printf '%s\n' '  return a + b;'
  printf '%s\n' '}'
  printf '%s\n' ''
  printf '%s\n' 'int main(void) {'
  printf '%s\n' '  return add(2, 40) - 42;'
  printf '%s\n' '}'
} > "${workdir}/hello.c"

test -x "${CHIBICC_BIN}"
"${CHIBICC_BIN}" -S -o "${workdir}/hello.s" "${workdir}/hello.c"
test -s "${workdir}/hello.s"
grep -q "main:" "${workdir}/hello.s"
grep -q "add:" "${workdir}/hello.s"
grep -q "call" "${workdir}/hello.s"
