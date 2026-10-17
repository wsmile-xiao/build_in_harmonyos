#!/system/bin/sh
set -eu

java_home=$1
work=$2
source_dir=$3
readelf=$4
patchelf=$5
freetype_libdir=$6
clang=$7
signer=$8

wait_for_file() {
  wait_path=$1
  wait_pid=$2
  wait_attempt=0
  while [ ! -s "$wait_path" ] && kill -0 "$wait_pid" 2>/dev/null; do
    wait_attempt=$((wait_attempt + 1))
    if [ "$wait_attempt" -ge 15 ]; then
      return 1
    fi
    sleep 1
  done
  [ -s "$wait_path" ]
}

terminate_wrapper() {
  terminate_pid=$1
  terminate_driver_file=${2:-}
  if kill -0 "$terminate_pid" 2>/dev/null; then
    kill -TERM "$terminate_pid" 2>/dev/null || true
    terminate_attempt=0
    while kill -0 "$terminate_pid" 2>/dev/null; do
      terminate_attempt=$((terminate_attempt + 1))
      if [ "$terminate_attempt" -ge 5 ]; then
        kill -KILL "$terminate_pid" 2>/dev/null || true
        break
      fi
      sleep 1
    done
  fi
  wait "$terminate_pid" 2>/dev/null || true
  if [ -n "$terminate_driver_file" ] && [ -s "$terminate_driver_file" ]; then
    terminate_driver_pid="$(cat "$terminate_driver_file")"
    case "$terminate_driver_pid" in
      ''|*[!0-9]*) return ;;
    esac
    terminate_driver_command=
    if [ -r "/proc/$terminate_driver_pid/cmdline" ]; then
      terminate_driver_command="$(tr '\000' ' ' \
        < "/proc/$terminate_driver_pid/cmdline")"
    fi
    case "$terminate_driver_command" in
      *"$fake_java/bin/native-image.real"*) ;;
      *) return ;;
    esac
    if kill -0 "$terminate_driver_pid" 2>/dev/null; then
      kill -TERM "$terminate_driver_pid" 2>/dev/null || true
      terminate_driver_attempt=0
      while kill -0 "$terminate_driver_pid" 2>/dev/null; do
        terminate_driver_attempt=$((terminate_driver_attempt + 1))
        if [ "$terminate_driver_attempt" -ge 5 ]; then
          kill -KILL "$terminate_driver_pid" 2>/dev/null || true
          break
        fi
        sleep 1
      done
    fi
  fi
}

register_wrapper() {
  register_pid=$1
  register_driver_file=$2
  active_wrappers="${active_wrappers:+$active_wrappers }$register_pid|$register_driver_file"
}

forget_wrapper() {
  forget_pid=$1
  remaining_wrappers=
  for wrapper_record in $active_wrappers; do
    registered_pid=${wrapper_record%%|*}
    if [ "$registered_pid" != "$forget_pid" ]; then
      remaining_wrappers="${remaining_wrappers:+$remaining_wrappers }$wrapper_record"
    fi
  done
  active_wrappers=$remaining_wrappers
}

cleanup_test() {
  cleanup_status=$1
  trap - EXIT HUP INT TERM
  for wrapper_record in $active_wrappers; do
    cleanup_pid=${wrapper_record%%|*}
    cleanup_driver_file=${wrapper_record#*|}
    terminate_wrapper "$cleanup_pid" "$cleanup_driver_file"
  done
  active_wrappers=
  rm -rf "$work" || true
  exit "$cleanup_status"
}

assert_no_wrapper_residue() {
  residue_dir=$1
  [ ! -e "$residue_dir/.t" ]
  [ -z "$(find "$residue_dir" -maxdepth 1 -type d \
    -name '.*.graalvm-ohos-stage-*' -print -quit)" ]
  [ -z "$(find "$residue_dir" -maxdepth 1 \
    -name '.*.graalvm-ohos-backup-*' -print -quit)" ]
}

try_symlink() {
  symlink_target=$1
  symlink_path=$2
  symlink_log=$3
  last_symlink_error=
  if ln -s "$symlink_target" "$symlink_path" 2>"$symlink_log"; then
    return 0
  fi
  if grep -E 'Permission denied|Operation not permitted|Function not implemented' \
      "$symlink_log" >/dev/null; then
    [ ! -e "$symlink_path" ]
    last_symlink_error="$(tr '\n' ' ' < "$symlink_log")"
    return 1
  fi
  cat "$symlink_log" >&2
  exit 1
}

record_symlink_skip() {
  skip_label=$1
  native_image_symlink_skips=$((native_image_symlink_skips + 1))
  printf 'NATIVE_IMAGE_SYMLINK_SKIP=%s:%s\n' \
    "$skip_label" "$last_symlink_error"
}

run_to_log() {
  run_log=$1
  shift
  if "$@" >"$run_log" 2>&1; then
    return 0
  else
    run_status=$?
  fi
  cat "$run_log" >&2
  return "$run_status"
}

rm -rf "$work"
mkdir -p "$work/classes" "$work/tmp"
active_wrappers=
native_image_launcher_assertions=24
native_image_reserved_output_assertions=5
native_image_wrapper_negative_assertions=31
native_image_scratch_assertions=15
native_image_symlink_skips=0
trap 'cleanup_test $?' EXIT
trap 'cleanup_test 129' HUP
trap 'cleanup_test 130' INT
trap 'cleanup_test 143' TERM

export JAVA_HOME="$java_home"
export PATH="$JAVA_HOME/bin:$PATH"
unset LD_LIBRARY_PATH
export TMPDIR="$work/tmp"
export TMPPREFIX="$work/tmp"
export LD_BIND_NOW=1

[ -z "${LD_LIBRARY_PATH:-}" ]
[ -z "${JAVA_TOOL_OPTIONS:-}" ]
[ -z "${_JAVA_OPTIONS:-}" ]
[ -z "${JDK_JAVA_OPTIONS:-}" ]

"$clang" -O2 -Wl,-z,relro,-z,now \
  -Wl,-rpath,"$java_home/lib" \
  "$source_dir/compat_smoke.c" \
  -L"$java_home/lib" -Wl,-l:libg.so \
  -o "$work/compat-smoke.unsigned"
"$signer" sign \
  -inFile "$work/compat-smoke.unsigned" \
  -outFile "$work/compat-smoke" \
  -selfSign 1
chmod 750 "$work/compat-smoke"
compat_output="$(
  "$work/compat-smoke" "$work/passwd.fixture" "$work/group.fixture"
)"
printf '%s\n' "$compat_output"
printf '%s\n' "$compat_output" | \
  grep -Fx 'GCOMPAT_ABI_ASSERTIONS=66/66' >/dev/null
"$readelf" --dyn-syms --wide "$java_home/lib/libg.so" \
  >"$work/libg-dynsym.log"
if awk '$8 ~ /^__environ(@|$)/ && $7 != "UND" { found = 1 } \
    END { exit(found ? 0 : 1) }' "$work/libg-dynsym.log"; then
  printf 'libg.so must not define loader-owned __environ\n' >&2
  exit 1
fi
printf 'GCOMPAT_ELF_ASSERTIONS=1/1\n'

java_version="$work/java-version.log"
java -XX:ActiveProcessorCount=1 -version >"$java_version" 2>&1
grep -F 'openjdk version "25.0.3"' "$java_version" >/dev/null
grep -F 'GraalVM CE 25.1.3+9.1' "$java_version" >/dev/null

javac -J-XX:ActiveProcessorCount=1 -d "$work/classes" "$source_dir/GraalSmoke.java"
class_output="$(java -XX:ActiveProcessorCount=1 -cp "$work/classes" GraalSmoke)"
printf '%s\n' "$class_output"
printf '%s\n' "$class_output" | grep -F 'JAVA_SMOKE_OK=GraalVM Community:42' >/dev/null

for unsupported in \
  bin/jconsole \
  lib/libawt_xawt.so \
  lib/libjawt.so \
  lib/libjsound.so \
  lib/libsplashscreen.so
do
  [ ! -e "$java_home/$unsupported" ]
done
[ -f "$java_home/lib/libawt_headless.so" ]
[ -f "$java_home/lib/libfontmanager.so" ]

adaptation_output="$(python3 "$source_dir/validate_adaptation_report.py" \
  "$java_home/share/graalvm/ohos-adaptation.json" \
  "$java_home/lib/libfontmanager.so" \
  "$readelf" \
  "$source_dir/HeadlessSmoke.java" \
  "$java_home/conf/fonts/fontconfig.HarmonyOS.properties")"
printf '%s\n' "$adaptation_output"
printf '%s\n' "$adaptation_output" | \
  grep -Fx 'GRAALVM_ADAPTATION_REPORT_ASSERTIONS=15/15' >/dev/null

javac -J-XX:ActiveProcessorCount=1 -d "$work/classes" \
  "$source_dir/FontManagerLoadSmoke.java"
font_load_output="$(LD_LIBRARY_PATH="$freetype_libdir" \
  java -XX:ActiveProcessorCount=1 --enable-native-access=ALL-UNNAMED \
  -cp "$work/classes" FontManagerLoadSmoke \
  "$java_home/lib/libfontmanager.so")"
printf '%s\n' "$font_load_output"
printf '%s\n' "$font_load_output" | \
  grep -Fx 'JAVA_FONT_MANAGER_LOAD_OK=true' >/dev/null

javac -J-XX:ActiveProcessorCount=1 -d "$work/classes" \
  "$source_dir/HeadlessSmoke.java"
headless_output="$(LD_LIBRARY_PATH="$freetype_libdir" \
  java -XX:ActiveProcessorCount=1 -Djava.awt.headless=true \
  -Dsun.java2d.debugfonts=true -cp "$work/classes" HeadlessSmoke 2>&1)"
printf '%s\n' "$headless_output"
printf '%s\n' "$headless_output" | grep -Fx 'JAVA_OS_NAME=HarmonyOS' >/dev/null
printf '%s\n' "$headless_output" | \
  grep -Fx 'JAVA_FONTCONFIG_OVERRIDE=unset' >/dev/null
printf '%s\n' "$headless_output" | \
  grep -F "Found file : $java_home/conf/fonts/fontconfig.HarmonyOS.properties" \
  >/dev/null
printf '%s\n' "$headless_output" | grep -Fx 'JAVA_HEADLESS_OK=true' >/dev/null
[ -z "${LD_LIBRARY_PATH:-}" ]

jar --create --file "$work/graal-smoke.jar" \
  --manifest "$source_dir/MANIFEST.MF" -C "$work/classes" .
jar --list --file "$work/graal-smoke.jar" >"$work/jar-list.log"
grep -Fx 'GraalSmoke.class' "$work/jar-list.log" >/dev/null
grep -Fx 'META-INF/MANIFEST.MF' "$work/jar-list.log" >/dev/null
jar_output="$(java -XX:ActiveProcessorCount=1 -jar "$work/graal-smoke.jar")"
printf '%s\n' "$jar_output"
printf '%s\n' "$jar_output" | grep -F 'JAVA_SMOKE_OK=GraalVM Community:42' >/dev/null

[ "$("$patchelf" --print-rpath "$java_home/bin/native-image.real")" = \
  '$ORIGIN/../lib' ]
[ "$("$patchelf" --print-rpath \
  "$java_home/lib/svm/bin/native-image.real")" = '$ORIGIN/../../../lib' ]

for launcher in \
  "$java_home/bin/native-image" \
  "$java_home/lib/svm/bin/native-image"
do
  [ -x "$launcher" ]
  [ -f "$launcher.py" ]
  [ -f "$launcher.real" ]
  "$readelf" -h "$launcher" | grep -F 'AArch64' >/dev/null
  "$readelf" -lW "$launcher" | \
    grep -F '[Requesting program interpreter: /lib/ld-musl-aarch64.so.1]' \
    >/dev/null
  launcher_needed="$("$readelf" -dW "$launcher" | \
    awk '/Shared library:/ { value = $0; sub(/^.*\[/, "", value); \
      sub(/\].*$/, "", value); print value }')"
  [ "$launcher_needed" = 'libc.so' ]
  [ -z "$("$patchelf" --print-rpath "$launcher")" ]
  launcher_codesign_count="$(
    "$readelf" -SW "$launcher" | \
      awk 'index($0, " .codesign ") { count++ } END { print count + 0 }'
  )"
  [ "$launcher_codesign_count" -eq 1 ]
done

run_to_log "$work/native-image-version.log" native-image --version
grep -F 'native-image 25.0.3' "$work/native-image-version.log" >/dev/null
run_to_log "$work/native-image-svm-version.log" \
  "$java_home/lib/svm/bin/native-image" --version
grep -F 'native-image 25.0.3' "$work/native-image-svm-version.log" >/dev/null

if try_symlink "$java_home/bin/native-image" "$work/native-image-alias" \
    "$work/native-image-alias.ln.log"; then
  run_to_log "$work/native-image-alias.log" \
    "$work/native-image-alias" --version
  grep -F 'native-image 25.0.3' "$work/native-image-alias.log" >/dev/null
  rm -f "$work/native-image-alias"
else
  native_image_launcher_assertions=$((native_image_launcher_assertions - 1))
  record_symlink_skip native-image-alias
fi

if ! (PATH=/graalvm-intentionally-missing \
    "$java_home/bin/native-image" --version \
    >"$work/native-image-fixed-python.log" 2>&1); then
  cat "$work/native-image-fixed-python.log" >&2
  exit 1
fi
grep -F 'native-image 25.0.3' "$work/native-image-fixed-python.log" >/dev/null

mkdir -p "$work/blocked-python"
: >"$work/blocked-python/python3"
chmod 600 "$work/blocked-python/python3"
if ! (PATH="$work/blocked-python" \
    "$java_home/bin/native-image" --version \
    >"$work/native-image-blocked-python.log" 2>&1); then
  cat "$work/native-image-blocked-python.log" >&2
  exit 1
fi
grep -F 'native-image 25.0.3' "$work/native-image-blocked-python.log" >/dev/null

mkdir -p "$work/missing-companion"
cp "$java_home/bin/native-image" "$work/missing-companion/native-image"
missing_companion_status=0
"$work/missing-companion/native-image" --version \
  >"$work/native-image-missing-companion.log" 2>&1 || \
  missing_companion_status=$?
[ "$missing_companion_status" -eq 126 ]
grep -F 'graalvm native-image Python companion is missing:' \
  "$work/native-image-missing-companion.log" >/dev/null
printf 'NATIVE_IMAGE_LAUNCHER_ASSERTIONS=%s/%s\n' \
  "$native_image_launcher_assertions" "$native_image_launcher_assertions"

fake_java="$work/fake-java"
mkdir -p "$fake_java/bin" "$fake_java/lib" \
  "$fake_java/libexec/graalvm-ohos"
cp "$java_home/bin/native-image" "$fake_java/bin/native-image"
cp "$java_home/bin/native-image.py" "$fake_java/bin/native-image.py"
cp "$java_home/lib/libg.so" "$fake_java/lib/libg.so"
: >"$fake_java/libexec/graalvm-ohos/ohos-native-image-compat.h"
cp "$java_home/libexec/graalvm-ohos/elf_rewriter.py" \
  "$fake_java/libexec/graalvm-ohos/elf_rewriter.py"
cp "$java_home/libexec/graalvm-ohos/native_image_finalizer.py" \
  "$fake_java/libexec/graalvm-ohos/native_image_finalizer.py"
"$clang" -O2 "$source_dir/stale_native_driver.c" \
  -o "$work/stale-native-driver.unsigned"
"$signer" sign \
  -inFile "$work/stale-native-driver.unsigned" \
  -outFile "$fake_java/bin/native-image.real" \
  -selfSign 1
chmod 750 "$fake_java/bin/native-image.real"
fake_native_image_command="$fake_java/bin/native-image"
if try_symlink "$fake_java/bin/native-image" "$work/fake-native-image-alias" \
    "$work/fake-native-image-alias.ln.log"; then
  fake_native_image_command="$work/fake-native-image-alias"
else
  native_image_wrapper_negative_assertions=$((native_image_wrapper_negative_assertions - 1))
  record_symlink_skip fake-native-image-alias
fi

reserved_work="$work/reserved-output-contract"
mkdir -p "$reserved_work"
assert_reserved_output() {
  label=$1
  destination=$2
  expected_error=$3
  reserved_status=0
  (cd "$reserved_work" && "$fake_java/bin/native-image" --emit-output \
    -o "$destination" >"$reserved_work/$label.log" 2>&1) || \
    reserved_status=$?
  [ "$reserved_status" -ne 0 ]
  if ! grep -F "$expected_error" "$reserved_work/$label.log" >/dev/null; then
    cat "$reserved_work/$label.log" >&2
    exit 1
  fi
  [ ! -e "$destination" ]
  assert_no_wrapper_residue "$reserved_work"
}
assert_reserved_output scratch "$reserved_work/.t" \
  'Native Image output must not use scratch path'
assert_reserved_output lock "$reserved_work/.graalvm-native-image.lock" \
  'Native Image output must not replace a lock'
assert_reserved_output sidecar "$reserved_work/libg.so" \
  'Native Image output must not be named libg.so'
cp "$fake_java/lib/libg.so" "$reserved_work/libg.so"
cp "$reserved_work/libg.so" "$reserved_work/libg.so.before"
existing_sidecar_status=0
(cd "$reserved_work" && "$fake_java/bin/native-image" --emit-output \
  -o "$reserved_work/libg.so" \
  >"$reserved_work/existing-sidecar.log" 2>&1) || \
  existing_sidecar_status=$?
[ "$existing_sidecar_status" -ne 0 ]
grep -F 'Native Image output must not be named libg.so' \
  "$reserved_work/existing-sidecar.log" >/dev/null
cmp -s "$reserved_work/libg.so.before" "$reserved_work/libg.so"
rm -f "$reserved_work/libg.so" "$reserved_work/libg.so.before"
assert_no_wrapper_residue "$reserved_work"
if try_symlink .t "$reserved_work/scratch-alias" \
    "$reserved_work/scratch-alias.ln.log"; then
  assert_reserved_output scratch-alias "$reserved_work/scratch-alias/output" \
    'Native Image output must not use scratch path'
  rm -f "$reserved_work/scratch-alias"
else
  native_image_reserved_output_assertions=$((native_image_reserved_output_assertions - 1))
  record_symlink_skip reserved-scratch-alias
fi
printf 'NATIVE_IMAGE_RESERVED_OUTPUT_ASSERTIONS=%s/%s\n' \
  "$native_image_reserved_output_assertions" "$native_image_reserved_output_assertions"

cp "$fake_java/bin/native-image.real" "$work/stale-output"
if (cd "$work" && "$fake_java/bin/native-image" -o "$work/stale-output" \
    >"$work/stale-output.log" 2>&1); then
  printf 'wrapper accepted a touch-only explicit output\n' >&2
  exit 1
fi
grep -F 'Native Image did not create explicit output' \
  "$work/stale-output.log" >/dev/null
cmp -s "$fake_java/bin/native-image.real" "$work/stale-output"
if try_symlink "$work/stale-output" "$work/symlink-output" \
    "$work/symlink-output.ln.log"; then
  if (cd "$work" && \
      "$fake_java/bin/native-image" -o "$work/symlink-output" \
      >"$work/symlink-output.log" 2>&1); then
    printf 'wrapper accepted a symbolic-link output\n' >&2
    exit 1
  fi
  grep -F 'Native Image output must not be a symlink' \
    "$work/symlink-output.log" >/dev/null
  rm -f "$work/symlink-output"
else
  native_image_wrapper_negative_assertions=$((native_image_wrapper_negative_assertions - 1))
  record_symlink_skip native-image-output-symlink
fi

if (cd "$work" && \
    JAVA_TOOL_OPTIONS=-Dgraalvm.forbidden=true \
    JDK_JAVA_OPTIONS=-Dgraalvm.forbidden=true \
    LD_LIBRARY_PATH=/graalvm-intentionally-missing \
    PYTHONHOME=/graalvm-intentionally-missing \
    PYTHONPATH=/graalvm-intentionally-missing \
    _JAVA_OPTIONS=-Dgraalvm.forbidden=true \
    "$fake_native_image_command" --require-sanitized-environment \
    --expect-special-arguments 'value with space' '' \
    --emit-output -o "$work/new-output" \
    >"$work/new-output.log" 2>&1); then
  printf 'wrapper accepted an unfinalized new explicit output\n' >&2
  exit 1
fi
grep -F 'Native Image output does not depend on libg.so' \
  "$work/new-output.log" >/dev/null
[ ! -e "$work/new-output" ]
assert_no_wrapper_residue "$work"

printf 'previous explicit output\n' >"$work/existing-output"
cp "$work/existing-output" "$work/existing-output.before"
if (cd "$work" && "$fake_java/bin/native-image" --emit-output \
    -o "$work/existing-output" >"$work/existing-output.log" 2>&1); then
  printf 'wrapper accepted an unfinalized replacement explicit output\n' >&2
  exit 1
fi
grep -F 'Native Image output does not depend on libg.so' \
  "$work/existing-output.log" >/dev/null
cmp -s "$work/existing-output.before" "$work/existing-output"

if (cd "$work" && "$fake_java/bin/native-image" --emit-output \
    >"$work/implicit-output.log" 2>&1); then
  printf 'wrapper accepted a build without an explicit output\n' >&2
  exit 1
fi
grep -F 'requires an explicit -o/--output path' \
  "$work/implicit-output.log" >/dev/null
[ ! -e "$work/implicit-output" ]

if (cd "$work" && "$fake_java/bin/native-image" --emit-partial-failure \
    -o "$work/partial-new" >"$work/partial-new.log" 2>&1); then
  printf 'wrapper accepted a partial new explicit output\n' >&2
  exit 1
fi
[ ! -e "$work/partial-new" ]
[ -z "$(find "$work" -maxdepth 1 \
  -name '.partial-new.graalvm-ohos-stage-*' -print -quit)" ]

printf 'previous partial output\n' >"$work/partial-existing"
cp "$work/partial-existing" "$work/partial-existing.before"
if (cd "$work" && "$fake_java/bin/native-image" --emit-partial-failure \
    -o "$work/partial-existing" >"$work/partial-existing.log" 2>&1); then
  printf 'wrapper accepted a partial replacement explicit output\n' >&2
  exit 1
fi
cmp -s "$work/partial-existing.before" "$work/partial-existing"
[ -z "$(find "$work" -maxdepth 1 \
  -name '.partial-existing.graalvm-ohos-stage-*' -print -quit)" ]
assert_no_wrapper_residue "$work"
printf 'NATIVE_IMAGE_WRAPPER_NEGATIVE_ASSERTIONS=%s/%s\n' \
  "$native_image_wrapper_negative_assertions" "$native_image_wrapper_negative_assertions"

cas_work="$work/destination-cas-contract"
mkdir -p "$cas_work"
printf 'original destination\n' >"$cas_work/output"
cas_status=0
(cd "$cas_work" && "$fake_java/bin/native-image" --emit-output \
  --copy-source "$work/compat-smoke" \
  --mutate-destination "$cas_work/output" \
  -o "$cas_work/output" >"$cas_work/cas.log" 2>&1) || cas_status=$?
[ "$cas_status" -ne 0 ]
grep -F 'Native Image output changed during finalization' \
  "$cas_work/cas.log" >/dev/null
grep -Fx 'concurrent destination' "$cas_work/output" >/dev/null
[ ! -e "$cas_work/libg.so" ]
assert_no_wrapper_residue "$cas_work"
printf 'NATIVE_IMAGE_TRANSACTION_ASSERTIONS=5/5\n'

transaction_signal_output="$(python3 \
  "$source_dir/native_image_transaction_test.py" \
  "$fake_java/bin/native-image.py" \
  "$work/transaction-signal-contract")"
printf '%s\n' "$transaction_signal_output"
printf '%s\n' "$transaction_signal_output" | \
  grep -Fx 'NATIVE_IMAGE_TRANSACTION_SIGNAL_ASSERTIONS=62/62' >/dev/null
printf '%s\n' "$transaction_signal_output" | \
  grep -Fx 'NATIVE_IMAGE_OUTPUT_CAS_ASSERTIONS=49/49' >/dev/null
printf '%s\n' "$transaction_signal_output" | \
  grep -Fx 'NATIVE_IMAGE_CLEANUP_CAS_ASSERTIONS=27/27' >/dev/null
native_image_finalizer_symlink_skips="$(
  printf '%s\n' "$transaction_signal_output" | \
    awk -F= '/^NATIVE_IMAGE_FINALIZER_SYMLINK_SKIPPED_ASSERTIONS=/ { print $2 }'
)"
: "${native_image_finalizer_symlink_skips:=0}"
native_image_finalizer_assertions=$((81 - native_image_finalizer_symlink_skips))
printf '%s\n' "$transaction_signal_output" | \
  grep -Fx \
    "NATIVE_IMAGE_FINALIZER_CAS_ASSERTIONS=$native_image_finalizer_assertions/$native_image_finalizer_assertions" \
    >/dev/null
printf '%s\n' "$transaction_signal_output" | \
  grep -Fx 'NATIVE_IMAGE_TRANSACTION_ROLLBACK_ASSERTIONS=16/16' >/dev/null
printf '%s\n' "$transaction_signal_output" | \
  grep -Fx 'NATIVE_IMAGE_LIBG_CAS_ASSERTIONS=19/19' >/dev/null

scratch_work="$work/scratch-contract"
mkdir -p "$scratch_work"
if try_symlink "$work/tmp" "$scratch_work/.t" \
    "$scratch_work/symlink-scratch.ln.log"; then
  if (cd "$scratch_work" && "$fake_java/bin/native-image" --emit-output \
      -o "$scratch_work/symlink-scratch-output" \
      >"$scratch_work/symlink-scratch.log" 2>&1); then
    printf 'wrapper accepted a symbolic-link scratch path\n' >&2
    exit 1
  fi
  grep -F 'scratch path is not a private owned directory' \
    "$scratch_work/symlink-scratch.log" >/dev/null
  [ -L "$scratch_work/.t" ]
  [ ! -e "$scratch_work/symlink-scratch-output" ]
  rm -f "$scratch_work/.t"
else
  native_image_scratch_assertions=$((native_image_scratch_assertions - 1))
  record_symlink_skip native-image-scratch-symlink
fi

printf 'not a directory\n' >"$scratch_work/.t"
if (cd "$scratch_work" && "$fake_java/bin/native-image" --emit-output \
    -o "$scratch_work/insecure-scratch-output" \
    >"$scratch_work/insecure-scratch.log" 2>&1); then
  printf 'wrapper accepted a non-private scratch path\n' >&2
  exit 1
fi
if ! grep -F 'scratch path is not a private owned directory' \
    "$scratch_work/insecure-scratch.log" >/dev/null; then
  cat "$scratch_work/insecure-scratch.log" >&2
  exit 1
fi
[ -f "$scratch_work/.t" ]
[ ! -e "$scratch_work/insecure-scratch-output" ]
rm -f "$scratch_work/.t"

mkdir "$scratch_work/.t"
chmod 700 "$scratch_work/.t"
: >"$scratch_work/.t/stale"
if (cd "$scratch_work" && "$fake_java/bin/native-image" --emit-output \
    -o "$scratch_work/stale-scratch-output" \
    >"$scratch_work/stale-scratch.log" 2>&1); then
  printf 'wrapper accepted an existing scratch directory\n' >&2
  exit 1
fi
if grep -F 'Native Image scratch path already exists; refusing to remove' \
    "$scratch_work/stale-scratch.log" >/dev/null; then
  :
elif grep -F 'scratch path is not a private owned directory' \
    "$scratch_work/stale-scratch.log" >/dev/null; then
  :
else
  cat "$scratch_work/stale-scratch.log" >&2
  exit 1
fi
[ -f "$scratch_work/.t/stale" ]
[ ! -e "$scratch_work/stale-scratch-output" ]
rm -rf "$scratch_work/.t"
assert_no_wrapper_residue "$scratch_work"
printf 'NATIVE_IMAGE_SCRATCH_ASSERTIONS=%s/%s\n' \
  "$native_image_scratch_assertions" "$native_image_scratch_assertions"

exit_work="$work/exit-contract"
mkdir -p "$exit_work"
printf 'previous ordinary output\n' >"$exit_work/ordinary-output"
cp "$exit_work/ordinary-output" "$exit_work/ordinary-output.before"
ordinary_status=0
(cd "$exit_work" && "$fake_java/bin/native-image" --exit-code 23 \
  -o "$exit_work/ordinary-output" \
  >"$exit_work/ordinary.log" 2>&1) || ordinary_status=$?
[ "$ordinary_status" -eq 23 ]
cmp -s "$exit_work/ordinary-output.before" "$exit_work/ordinary-output"
assert_no_wrapper_residue "$exit_work"

printf 'previous self-signal output\n' >"$exit_work/self-signal-output"
cp "$exit_work/self-signal-output" "$exit_work/self-signal-output.before"
self_signal_status=0
(cd "$exit_work" && "$fake_java/bin/native-image" --raise-signal TERM \
  -o "$exit_work/self-signal-output" \
  >"$exit_work/self-signal.log" 2>&1) || self_signal_status=$?
[ "$self_signal_status" -eq 143 ]
cmp -s "$exit_work/self-signal-output.before" \
  "$exit_work/self-signal-output"
assert_no_wrapper_residue "$exit_work"
printf 'NATIVE_IMAGE_EXIT_ASSERTIONS=10/10\n'

run_signal_restore_test() {
  signal_name=$1
  expected_status=$2
  label=$3
  signal_work="$work/signal-$label"
  signal_output="$signal_work/output"
  signal_before="$signal_work/output.before"
  signal_pid="$signal_work/driver.pid"
  signal_log="$signal_work/wrapper.log"
  rm -rf "$signal_work"
  mkdir -p "$signal_work"
  printf 'previous %s output\n' "$label" >"$signal_output"
  cp "$signal_output" "$signal_before"

  (
    cd "$signal_work"
    exec "$fake_java/bin/native-image" --sleep-after-output \
      --pid-file "$signal_pid" -o "$signal_output" \
      >"$signal_log" 2>&1
  ) &
  wrapper_pid=$!
  register_wrapper "$wrapper_pid" "$signal_pid"

  if ! wait_for_file "$signal_pid" "$wrapper_pid"; then
    terminate_wrapper "$wrapper_pid" "$signal_pid"
    forget_wrapper "$wrapper_pid"
    cat "$signal_log" >&2
    return 1
  fi

  kill -s "$signal_name" "$wrapper_pid"
  wrapper_status=0
  wait "$wrapper_pid" || wrapper_status=$?
  [ "$wrapper_status" -eq "$expected_status" ]
  cmp -s "$signal_before" "$signal_output"
  assert_no_wrapper_residue "$signal_work"
  driver_pid="$(cat "$signal_pid")"
  if kill -0 "$driver_pid" 2>/dev/null; then
    printf '%s driver process remains after signal forwarding\n' "$label" >&2
    return 1
  fi
  forget_wrapper "$wrapper_pid"
}

run_signal_restore_test TERM 143 term
run_signal_restore_test HUP 129 hup
run_signal_restore_test INT 130 int
printf 'NATIVE_IMAGE_SIGNAL_ASSERTIONS=21/21\n'

concurrent_work="$work/concurrent-contract"
mkdir -p "$concurrent_work"
printf 'previous first output\n' >"$concurrent_work/first-output"
printf 'previous second output\n' >"$concurrent_work/second-output"
cp "$concurrent_work/first-output" "$concurrent_work/first-output.before"
cp "$concurrent_work/second-output" "$concurrent_work/second-output.before"
(
  cd "$concurrent_work"
  exec "$fake_java/bin/native-image" --sleep-after-output \
    --pid-file "$concurrent_work/first.pid" \
    -o "$concurrent_work/first-output" \
    >"$concurrent_work/first.log" 2>&1
) &
first_wrapper_pid=$!
register_wrapper "$first_wrapper_pid" "$concurrent_work/first.pid"
if ! wait_for_file "$concurrent_work/first.pid" "$first_wrapper_pid"; then
  terminate_wrapper "$first_wrapper_pid" "$concurrent_work/first.pid"
  forget_wrapper "$first_wrapper_pid"
  cat "$concurrent_work/first.log" >&2
  exit 1
fi
(
  cd "$concurrent_work"
  exec "$fake_java/bin/native-image" --sleep-after-output \
    --pid-file "$concurrent_work/second.pid" \
    -o "$concurrent_work/second-output" \
    >"$concurrent_work/second.log" 2>&1
) &
second_wrapper_pid=$!
register_wrapper "$second_wrapper_pid" "$concurrent_work/second.pid"
sleep 1
if [ -e "$concurrent_work/second.pid" ]; then
  terminate_wrapper "$first_wrapper_pid" "$concurrent_work/first.pid"
  terminate_wrapper "$second_wrapper_pid" "$concurrent_work/second.pid"
  forget_wrapper "$first_wrapper_pid"
  forget_wrapper "$second_wrapper_pid"
  printf 'concurrent wrapper bypassed the scratch lock\n' >&2
  exit 1
fi
kill -s TERM "$first_wrapper_pid"
first_wrapper_status=0
wait "$first_wrapper_pid" || first_wrapper_status=$?
[ "$first_wrapper_status" -eq 143 ]
if ! wait_for_file "$concurrent_work/second.pid" "$second_wrapper_pid"; then
  terminate_wrapper "$second_wrapper_pid" "$concurrent_work/second.pid"
  forget_wrapper "$second_wrapper_pid"
  cat "$concurrent_work/second.log" >&2
  exit 1
fi
kill -s HUP "$second_wrapper_pid"
second_wrapper_status=0
wait "$second_wrapper_pid" || second_wrapper_status=$?
[ "$second_wrapper_status" -eq 129 ]
cmp -s "$concurrent_work/first-output.before" \
  "$concurrent_work/first-output"
cmp -s "$concurrent_work/second-output.before" \
  "$concurrent_work/second-output"
assert_no_wrapper_residue "$concurrent_work"
first_driver_pid="$(cat "$concurrent_work/first.pid")"
second_driver_pid="$(cat "$concurrent_work/second.pid")"
if kill -0 "$first_driver_pid" 2>/dev/null; then
  printf 'first concurrent Native Image driver remains after forwarding\n' >&2
  exit 1
fi
if kill -0 "$second_driver_pid" 2>/dev/null; then
  printf 'second concurrent Native Image driver remains after forwarding\n' >&2
  exit 1
fi
forget_wrapper "$first_wrapper_pid"
forget_wrapper "$second_wrapper_pid"
printf 'NATIVE_IMAGE_CONCURRENCY_ASSERTIONS=12/12\n'

native_image_status=0
(cd "$work" && nice -n 10 native-image \
    -O0 \
    --no-fallback \
    -cp "$work/classes" \
    GraalSmoke \
    -o "$work/graal-smoke") >"$work/native-image-build.log" 2>&1 || \
  native_image_status=$?
if [ "$native_image_status" -ne 0 ]; then
  cat "$work/native-image-build.log" >&2
  exit "$native_image_status"
fi

if ! grep -F 'OHOS_NATIVE_IMAGE_FINALIZED=' "$work/native-image-build.log" \
    >/dev/null; then
  cat "$work/native-image-build.log" >&2
  exit 1
fi
if ! grep -F '1 thread(s) (100.0% of 1 available processor(s)' \
    "$work/native-image-build.log" >/dev/null; then
  cat "$work/native-image-build.log" >&2
  exit 1
fi

[ -s "$work/graal-smoke" ]
"$readelf" -h "$work/graal-smoke" | grep -F 'AArch64' >/dev/null
"$readelf" -lW "$work/graal-smoke" | \
  grep -F '[Requesting program interpreter: /lib/ld-musl-aarch64.so.1]' >/dev/null
[ "$("$patchelf" --print-rpath "$work/graal-smoke")" = '$ORIGIN' ]
"$readelf" -dW "$work/graal-smoke" >"$work/native-dynamic.log"
grep -F 'Shared library: [libg.so]' "$work/native-dynamic.log" >/dev/null
for forbidden in ld-linux-aarch64.so.1 libc.so.6 libdl.so.2 libm.so.6 \
  libpthread.so.0 librt.so.1; do
  if grep -F "$forbidden" "$work/native-dynamic.log" >/dev/null; then
    printf 'forbidden GNU dependency remains: %s\n' "$forbidden" >&2
    exit 1
  fi
done
target_codesign_count="$(
  "$readelf" -SW "$work/graal-smoke" | \
    awk 'index($0, " .codesign ") { count++ } END { print count + 0 }'
)"
[ "$target_codesign_count" -eq 1 ]

[ -s "$work/libg.so" ]
"$readelf" -h "$work/libg.so" | grep -F 'AArch64' >/dev/null
libg_codesign_count="$(
  "$readelf" -SW "$work/libg.so" | \
    awk 'index($0, " .codesign ") { count++ } END { print count + 0 }'
)"
[ "$libg_codesign_count" -eq 1 ]

native_output="$("$work/graal-smoke")"
printf '%s\n' "$native_output"
printf '%s\n' "$native_output" | grep -F 'JAVA_SMOKE_OK=GraalVM Community:42' >/dev/null

printf 'GRAALVM_TEST_FLOWS=9/9\n'
graalvm_test_assertions=$((504 - native_image_symlink_skips - \
  native_image_finalizer_symlink_skips))
printf 'GRAALVM_TEST_SKIPPED_ASSERTIONS=%s\n' "$native_image_symlink_skips"
printf 'GRAALVM_TEST_ASSERTIONS=%s/%s\n' \
  "$graalvm_test_assertions" "$graalvm_test_assertions"
