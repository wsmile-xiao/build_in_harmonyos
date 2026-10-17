#!/usr/bin/env bash
set -euo pipefail

: "${CHIBICC_SOURCE_DIR:?set CHIBICC_SOURCE_DIR to the verified chibicc source tree}"

jobs=${CHIBICC_JOBS:-4}
test_timeout=${CHIBICC_TEST_TIMEOUT:-60}
results_root=${CHIBICC_RESULTS_DIR:-$PWD/chibicc-native-results}
source_dir=$(cd "${CHIBICC_SOURCE_DIR}" && pwd -P)
run_id=$(date -u +%Y%m%dT%H%M%SZ)
results_dir="${results_root%/}/${run_id}"
tmp_root=${TMPDIR:-/tmp}
tmp_root=${tmp_root%/}
work_dir=$(mktemp -d "${tmp_root}/chibicc-native.XXXXXX")

cleanup() {
  if [ "${CHIBICC_KEEP_WORK:-0}" != 1 ]; then
    case "${work_dir}" in
      "${tmp_root}"/chibicc-native.*)
        rm -rf "${work_dir}"
        ;;
      *)
        echo "refusing to remove unexpected work path: ${work_dir}" >&2
        ;;
    esac
  else
    echo "work tree retained: ${work_dir}"
  fi
}
trap cleanup EXIT

if [ "$(uname -m)" != x86_64 ]; then
  echo "native test requires an x86_64 Linux host" >&2
  exit 2
fi

for tool in bash gcc make timeout grep file awk; do
  command -v "${tool}" >/dev/null || {
    echo "missing required tool: ${tool}" >&2
    exit 2
  }
done

ldd_version=$(ldd --version 2>&1)
if ! grep -Eq 'GLIBC|GNU libc' <<<"${ldd_version}"; then
  echo "native test requires a glibc x86_64 userspace" >&2
  exit 2
fi

mkdir -p "${results_dir}"
cp -a "${source_dir}/." "${work_dir}/"
cd "${work_dir}"

test_source_count=$(find test -maxdepth 1 -type f -name '*.c' | wc -l)
if [ "${test_source_count}" -ne 980 ]; then
  echo "expected 980 test/*.c sources, found ${test_source_count}" >&2
  exit 3
fi

make clean >/dev/null 2>&1 || true
make -j"${jobs}" LDFLAGS= chibicc >"${results_dir}/stage1-build.log" 2>&1
test -x chibicc || {
  echo "stage1 compiler was not built" >&2
  exit 4
}

targets_for() {
  local stage=$1 source name
  for source in test/*.c; do
    case "${source}" in
      test/csmith_102.c|test/csmith_275.c|test/csmith_4204.c)
        continue
        ;;
    esac
    name=${source##*/}
    if [ "${stage}" = stage1 ]; then
      printf 'test/%s.exe\n' "${name%.c}"
    else
      printf 'stage2/test/%s.exe\n' "${name%.c}"
    fi
  done
}

run_stage() {
  local stage=$1 prefix=$2 compiler=$3
  local stage_dir="${results_dir}/${stage}"
  local target_file="${stage_dir}/targets.txt"
  local source name executable test_status result driver_status driver_result
  local built=0 running=0 pass=0 runtime_fail=0 compile_fail=0 blocked=0
  local manifest total
  local -a targets

  mkdir -p "${stage_dir}/logs" "${stage_dir}/status"
  targets_for "${stage}" >"${target_file}"
  mapfile -t targets <"${target_file}"
  if [ "${#targets[@]}" -ne 977 ]; then
    echo "${stage}: expected 977 non-Csmith targets, found ${#targets[@]}" >&2
    exit 5
  fi

  set +e
  make -j"${jobs}" -k LDFLAGS= "${targets[@]}" >"${stage_dir}/compile.log" 2>&1
  local make_status=$?
  set -e

  for executable in "${targets[@]}"; do
    [ -x "${executable}" ] && built=$((built + 1))
  done

  for source in test/*.c; do
    name=${source##*/}
    name=${name%.c}
    case "${name}" in
      csmith_102|csmith_275|csmith_4204)
        printf 'DEPENDENCY_BLOCKED\t127\n' >"${stage_dir}/status/${name}"
        continue
        ;;
    esac

    executable="${prefix}/${name}.exe"
    if [ ! -x "${executable}" ]; then
      printf 'COMPILE_FAIL\t127\n' >"${stage_dir}/status/${name}"
      continue
    fi

    (
      set +e
      timeout "${test_timeout}" "./${executable}" >"${stage_dir}/logs/${name}.log" 2>&1
      test_status=$?
      if [ "${test_status}" -eq 0 ]; then
        result=PASS
      else
        result=RUNTIME_FAIL
      fi
      printf '%s\t%s\n' "${result}" "${test_status}" >"${stage_dir}/status/${name}"
    ) &
    running=$((running + 1))
    if [ "${running}" -ge "${jobs}" ]; then
      wait -n
      running=$((running - 1))
    fi
  done
  wait

  set +e
  timeout 300 test/driver.sh "./${compiler}" >"${stage_dir}/driver.log" 2>&1
  driver_status=$?
  set -e
  if [ "${driver_status}" -eq 0 ]; then
    driver_result=PASS
  else
    driver_result=RUNTIME_FAIL
  fi

  manifest="${stage_dir}/manifest.tsv"
  printf 'stage\ttest\tstatus\texit_code\n' >"${manifest}"
  for source in test/*.c; do
    name=${source##*/}
    name=${name%.c}
    read -r result test_status <"${stage_dir}/status/${name}"
    printf '%s\t%s\t%s\t%s\n' "${stage}" "${name}" "${result}" "${test_status}" >>"${manifest}"
    case "${result}" in
      PASS) pass=$((pass + 1)) ;;
      RUNTIME_FAIL) runtime_fail=$((runtime_fail + 1)) ;;
      COMPILE_FAIL) compile_fail=$((compile_fail + 1)) ;;
      DEPENDENCY_BLOCKED) blocked=$((blocked + 1)) ;;
    esac
  done
  printf '%s\tdriver\t%s\t%s\n' "${stage}" "${driver_result}" "${driver_status}" >>"${manifest}"
  if [ "${driver_result}" = PASS ]; then
    pass=$((pass + 1))
  else
    runtime_fail=$((runtime_fail + 1))
  fi

  total=$((pass + runtime_fail + compile_fail + blocked))
  if [ "${total}" -ne 981 ]; then
    echo "${stage}: expected 981 accounted tests, found ${total}" >&2
    exit 6
  fi
  printf '%s: make_status=%s built=%s/977 pass=%s runtime_fail=%s compile_fail=%s dependency_blocked=%s total=%s\n' \
    "${stage}" "${make_status}" "${built}" "${pass}" "${runtime_fail}" \
    "${compile_fail}" "${blocked}" "${total}"
}

run_stage stage1 test chibicc

make -j"${jobs}" LDFLAGS= stage2/chibicc >"${results_dir}/stage2-bootstrap.log" 2>&1
stage2_objects=$(find stage2 -maxdepth 1 -type f -name '*.o' | wc -l)
if [ ! -x stage2/chibicc ] || [ "${stage2_objects}" -ne 13 ]; then
  echo "stage2 bootstrap requires 13 self-hosted objects; found ${stage2_objects}" >&2
  exit 7
fi

run_stage stage2 stage2/test stage2/chibicc

awk 'FNR == 1 && NR != 1 { next } { print }' \
  "${results_dir}/stage1/manifest.tsv" \
  "${results_dir}/stage2/manifest.tsv" \
  >"${results_dir}/native-x86_64-results.tsv"

row_count=$(($(wc -l <"${results_dir}/native-x86_64-results.tsv") - 1))
if [ "${row_count}" -ne 1962 ]; then
  echo "expected 1962 result rows, found ${row_count}" >&2
  exit 8
fi

awk -F '\t' '
  NR > 1 { count[$3]++ }
  END {
    printf "total: pass=%d runtime_fail=%d compile_fail=%d dependency_blocked=%d total=%d\n",
      count["PASS"], count["RUNTIME_FAIL"], count["COMPILE_FAIL"],
      count["DEPENDENCY_BLOCKED"], NR - 1
  }
' "${results_dir}/native-x86_64-results.tsv"
echo "results: ${results_dir}"
