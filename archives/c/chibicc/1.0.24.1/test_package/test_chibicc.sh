#!/usr/bin/env sh
set -eu

: "${CHIBICC_BIN:?CHIBICC_BIN is required}"
: "${CHIBICC_SOURCE_DIR:?CHIBICC_SOURCE_DIR is required}"
: "${CHIBICC_RUNTIME_DIR:?CHIBICC_RUNTIME_DIR is required}"
: "${CHIBICC_XFAILS:?CHIBICC_XFAILS is required}"

workdir="${PWD}/chibicc-smoke"
rm -rf "${workdir}"
mkdir -p "${workdir}/tmp" "${workdir}/upstream" "${workdir}/stage2"
export TMPDIR="${workdir}/tmp"
export TMPPREFIX="${workdir}/tmp/sh"
source_owned_list="${CHIBICC_RUNTIME_DIR}/source-owned-tests.txt"
target_header_blockers="${CHIBICC_RUNTIME_DIR}/target-header-blockers.txt"


write_case() {
  case_name="$1"
  src="${workdir}/${case_name}.c"

  case "${case_name}" in
    arithmetic_calls)
      {
        printf '%s\n' 'int add(int a, int b) {'
        printf '%s\n' '  return a + b;'
        printf '%s\n' '}'
        printf '%s\n' 'int main(void) {'
        printf '%s\n' '  return add(2, 40) - 42;'
        printf '%s\n' '}'
      } > "${src}"
      ;;
    pointer_array)
      {
        printf '%s\n' 'int sum(int *p, int n) {'
        printf '%s\n' '  int r = 0;'
        printf '%s\n' '  for (int i = 0; i < n; i = i + 1)'
        printf '%s\n' '    r = r + p[i];'
        printf '%s\n' '  return r;'
        printf '%s\n' '}'
        printf '%s\n' 'int main(void) {'
        printf '%s\n' '  int xs[4] = { 1, 2, 3, 4 };'
        printf '%s\n' '  return sum(xs, 4) - 10;'
        printf '%s\n' '}'
      } > "${src}"
      ;;
    struct_fields)
      {
        printf '%s\n' 'struct pair { int a; int b; };'
        printf '%s\n' 'int total(struct pair p) {'
        printf '%s\n' '  return p.a + p.b;'
        printf '%s\n' '}'
        printf '%s\n' 'int main(void) {'
        printf '%s\n' '  struct pair p = { 19, 23 };'
        printf '%s\n' '  return total(p) - 42;'
        printf '%s\n' '}'
      } > "${src}"
      ;;
    recursion_control)
      {
        printf '%s\n' 'int fact(int n) {'
        printf '%s\n' '  if (n <= 1)'
        printf '%s\n' '    return 1;'
        printf '%s\n' '  return n * fact(n - 1);'
        printf '%s\n' '}'
        printf '%s\n' 'int main(void) {'
        printf '%s\n' '  return fact(5) - 120;'
        printf '%s\n' '}'
      } > "${src}"
      ;;
    *)
      echo "unknown case: ${case_name}" >&2
      exit 2
      ;;
  esac
}

run_case() {
  case_name="$1"
  symbol="$2"
  src="${workdir}/${case_name}.c"
  asm="${workdir}/${case_name}.s"

  write_case "${case_name}"
  (
    cd "${CHIBICC_RUNTIME_DIR}"
    ./chibicc -S -o "${asm}" "${src}"
  )
  test -s "${asm}"
  grep -q "main:" "${asm}"
  grep -q "${symbol}:" "${asm}"
  grep -q "call" "${asm}"
}

print_failure_details() {
  failure_list="$1"
  detail_limit="$2"
  shown=0

  while IFS= read -r log; do
    test -n "${log}" || continue
    shown=$((shown + 1))
    test "${shown}" -le "${detail_limit}" || break
    echo "--- ${log##*/}" >&2
    tail -n 12 "${log}" >&2
  done < "${failure_list}"
}

print_failure_summaries() {
  failure_list="$1"

  while IFS= read -r log; do
    test -n "${log}" || continue
    summary=$(sed -n '/error:/p' "${log}" | tail -n 1)
    test -n "${summary}" || summary=$(tail -n 1 "${log}")
    printf '%s: %s\n' "${log##*/}" "${summary}" >&2
  done < "${failure_list}"
}

missing_target_header() {
  log="$1"
  sed -n     's/.*in include_file: \(.*\): cannot open file: No such file or directory.*/\1/p'     "${log}" | tail -n 1
}

known_xfail_kind() {
  name="$1"
  sed -n "s/^${name} //p" "${CHIBICC_XFAILS}"
}

matches_expected_diagnostic() {
  kind="$1"
  log="$2"

  case "${kind}" in
    const-expr)
      grep -Fq "in eval_const_expr: no expression" "${log}"
      ;;
    primary-expression)
      grep -Fq "in primary: expected an expression" "${log}"
      ;;
    token-paste)
      grep -Fq "in paste: invalid preprocessing token" "${log}"
      ;;
    redefinition-main)
      grep -Fq "in function: redefinition of main" "${log}"
      ;;
    line-directive)
      grep -Fq "line.c:500:" "${log}" &&
        grep -Fq "#define ASSERT(x, y)" "${log}"
      ;;
    qualifiers-static-assert)
      grep -Fq "qualifiers.c:35:" "${log}" &&
        grep -Fq '#define SASSERT(x) _Static_assert(x,"")' "${log}"
      ;;
    *)
      return 1
      ;;
  esac
}

run_upstream_compile_suite() {
  attempted=0
  compiled=0
  xfailed=0
  xpassed=0
  csmith_blocked=0
  target_header_blocked=0
  failed=0
  test_dir="${CHIBICC_SOURCE_DIR}/test"
  source_owned_expected=$(wc -l < "${source_owned_list}")
  source_owned_compiled=0
  source_owned_xfailed=0
  source_owned_failed=0
  target_header_blocker_count=$(wc -l < "${target_header_blockers}")
  xfail_expected=$(sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "${CHIBICC_XFAILS}" | wc -l)
  test "${source_owned_expected}" -eq 607
  test "${target_header_blocker_count}" -eq 1037
  test "${xfail_expected}" -eq 62
  blocked_list="${workdir}/upstream-target-header-blocked.txt"
  xfail_list="${workdir}/upstream-xfails.txt"
  xpass_list="${workdir}/upstream-xpasses.txt"
  failure_list="${workdir}/upstream-failures.txt"
  : > "${blocked_list}"
  : > "${xfail_list}"
  : > "${xpass_list}"
  : > "${failure_list}"
  test -f "${test_dir}/test.h"

  for blocked_source in csmith_102 csmith_275 csmith_4204; do
    test -f "${test_dir}/${blocked_source}.c"
    test "$(grep -c '^#include "csmith.h"$' "${test_dir}/${blocked_source}.c")" -eq 1
  done
  test ! -e "${CHIBICC_SOURCE_DIR}/csmith.h"
  test ! -e "${test_dir}/csmith.h"
  test ! -e "${CHIBICC_RUNTIME_DIR}/include/csmith.h"

  for src in "${test_dir}"/*.c; do
    test -f "${src}"
    attempted=$((attempted + 1))
    name=${src##*/}
    name=${name%.c}
    case "${name}" in
      csmith_102|csmith_275|csmith_4204)
        csmith_blocked=$((csmith_blocked + 1))
        continue
        ;;
    esac
    asm="${workdir}/upstream/${name}.s"
    log="${workdir}/upstream/${name}.log"
    xfail_kind=$(known_xfail_kind "${name}")

    if (
      cd "${CHIBICC_RUNTIME_DIR}/include"
      "${CHIBICC_RUNTIME_DIR}/chibicc" \
        -std=c11 \
        -g \
        -mavx2 \
        -I "${CHIBICC_RUNTIME_DIR}/include" \
        -I "${test_dir}" \
        -S \
        -o "${asm}" \
        "${src}"
    ) >"${log}" 2>&1 && test -s "${asm}"; then
      rm -f "${log}"
      compiled=$((compiled + 1))
      if test -n "${xfail_kind}"; then
        printf '%s: %s\n' "${name}" "${xfail_kind}" >> "${xpass_list}"
        xpassed=$((xpassed + 1))
      fi
      if grep -qx "${name}" "${source_owned_list}"; then
        source_owned_compiled=$((source_owned_compiled + 1))
      fi
    else
      if test -n "${xfail_kind}" &&
        matches_expected_diagnostic "${xfail_kind}" "${log}"; then
        rm -f "${asm}"
        printf '%s: %s\n' "${name}" "${xfail_kind}" >> "${xfail_list}"
        xfailed=$((xfailed + 1))
        if grep -qx "${name}" "${source_owned_list}"; then
          source_owned_xfailed=$((source_owned_xfailed + 1))
        fi
        continue
      fi
      missing_header=$(missing_target_header "${log}")
      if test -z "${xfail_kind}" && test -n "${missing_header}" &&
        ! grep -qx "${name}" "${source_owned_list}" &&
        grep -Fxq "upstream/${name} ${missing_header}" "${target_header_blockers}"; then
        rm -f "${asm}"
        printf '%s: %s\n' "${name}" "${missing_header}" >> "${blocked_list}"
        target_header_blocked=$((target_header_blocked + 1))
        continue
      fi
      rm -f "${asm}"
      if test -n "${xfail_kind}"; then
        printf 'diagnostic drift for known XFAIL %s (%s)\n' \
          "${name}" "${xfail_kind}" >> "${log}"
      fi
      printf '%s\n' "${log}" >> "${failure_list}"
      failed=$((failed + 1))
      if grep -qx "${name}" "${source_owned_list}"; then
        source_owned_failed=$((source_owned_failed + 1))
      fi
    fi
  done

  echo "upstream compile boundary: ${source_owned_compiled}/${source_owned_expected} source-owned PASS; ${source_owned_xfailed} source-owned XFAIL; ${source_owned_failed} source-owned unexpected failures; ${compiled} total PASS; ${xfailed}/${xfail_expected} XFAIL; ${xpassed} XPASS; ${target_header_blocked} x86_64-target-header-blocked; ${csmith_blocked} Csmith-blocked; ${failed} unexpected failures; ${attempted} inventoried"
  if test "${attempted}" -ne 980 ||
    test "${csmith_blocked}" -ne 3 ||
    test $((compiled + xfailed + target_header_blocked + csmith_blocked + failed)) -ne 980 ||
    test $((source_owned_compiled + source_owned_xfailed + source_owned_failed)) -ne "${source_owned_expected}" ||
    test "${xfailed}" -ne "${xfail_expected}" ||
    test "${xpassed}" -ne 0 ||
    test "${failed}" -ne 0; then
    if test "${xpassed}" -ne 0; then
      echo "upstream XPASS (remove the entry after confirming the new capability):" >&2
      cat "${xpass_list}" >&2
    fi
    if test "${xfailed}" -ne "${xfail_expected}"; then
      echo "upstream observed XFAILs (${xfailed}/${xfail_expected}):" >&2
      cat "${xfail_list}" >&2
    fi
    echo "upstream unexpected failures:" >&2
    while IFS= read -r log; do
      test -n "${log}" && echo "${log##*/}" >&2
    done < "${failure_list}"
    echo "upstream failure root causes:" >&2
    print_failure_summaries "${failure_list}"
    echo "upstream failure details (first 100):" >&2
    print_failure_details "${failure_list}" 100
    overall_failed=1
  fi
}

run_stage2_source_compile_suite() {
  attempted=0
  compiled=0
  target_header_blocked=0
  failed=0
  blocked_list="${workdir}/stage2-target-header-blocked.txt"
  failure_list="${workdir}/stage2-failures.txt"
  : > "${blocked_list}"
  : > "${failure_list}"

  for src in "${CHIBICC_SOURCE_DIR}"/*.c; do
    test -f "${src}"
    attempted=$((attempted + 1))
    name=${src##*/}
    name=${name%.c}
    asm="${workdir}/stage2/${name}.s"
    log="${workdir}/stage2/${name}.log"

    if (
      cd "${CHIBICC_RUNTIME_DIR}/include"
      "${CHIBICC_RUNTIME_DIR}/chibicc" \
        -std=c11 \
        -g \
        -fno-common \
        -I "${CHIBICC_RUNTIME_DIR}/include" \
        -I "${CHIBICC_SOURCE_DIR}" \
        -S \
        -o "${asm}" \
        "${src}"
    ) >"${log}" 2>&1 && test -s "${asm}"; then
      rm -f "${log}"
      compiled=$((compiled + 1))
    else
      missing_header=$(missing_target_header "${log}")
      if test -n "${missing_header}" &&
        grep -Fxq "stage2/${name} ${missing_header}" "${target_header_blockers}"; then
        rm -f "${asm}"
        printf '%s: %s\n' "${name}" "${missing_header}" >> "${blocked_list}"
        target_header_blocked=$((target_header_blocked + 1))
        continue
      fi
      rm -f "${asm}"
      printf '%s\n' "${log}" >> "${failure_list}"
      failed=$((failed + 1))
    fi
  done

  echo "stage2 source boundary: ${compiled} compiled; ${target_header_blocked} x86_64-target-header-blocked; ${failed} unexpected failures; ${attempted} inventoried"
  if test "${attempted}" -ne 13 ||
    test $((compiled + target_header_blocked + failed)) -ne 13 ||
    test "${failed}" -ne 0; then
    echo "stage2 unexpected failures:" >&2
    while IFS= read -r log; do
      test -n "${log}" && echo "${log##*/}" >&2
    done < "${failure_list}"
    echo "stage2 failure root causes:" >&2
    print_failure_summaries "${failure_list}"
    print_failure_details "${failure_list}" 13
    overall_failed=1
  fi
}
test -x "${CHIBICC_BIN}"
"${CHIBICC_BIN}" --version >/dev/null

overall_failed=0
run_case arithmetic_calls add
run_case pointer_array sum
run_case struct_fields total
run_case recursion_control fact
run_upstream_compile_suite
run_stage2_source_compile_suite
test "${overall_failed}" -eq 0
