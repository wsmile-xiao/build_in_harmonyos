#!/usr/bin/env sh
set -eu

export LC_ALL=C

if [ "$#" -ne 9 ]; then
    printf '[FAIL] expected 9 arguments, received %s\n' "$#" >&2
    exit 2
fi

fixture_dir=$1
output_dir=$2
as_bin=$3
ld_bin=$4
ar_bin=$5
nm_bin=$6
objdump_bin=$7
readelf_bin=$8
strip_bin=$9

mkdir -p "$output_dir"
case "$(uname -m)" in
    aarch64|arm64) fixture="$fixture_dir/fixture-aarch64.S" ;;
    *) fixture="$fixture_dir/fixture-x86_64.S" ;;
esac
object="$output_dir/fixture.o"
linked="$output_dir/fixture-linked.o"
archive="$output_dir/libfixture.a"
stripped="$output_dir/fixture-stripped.o"
header="$output_dir/readelf-header.txt"
disassembly="$output_dir/objdump-disassembly.txt"
symbols="$output_dir/nm-symbols.txt"
step_no=0

print_stream() {
    label=$1
    path=$2
    printf '[%s]\n' "$label"
    if [ -s "$path" ]; then
        cat "$path"
    else
        printf '<empty>\n'
    fi
}

assert_matches() {
    pattern=$1
    path=$2
    description=$3
    expected=$4
    if grep -Eq "$pattern" "$path"; then
        printf '[PASS] %s\n' "$description"
        return 0
    fi
    printf '[FAIL] %s\n' "$description" >&2
    printf '[EXPECTED] %s\n' "$expected" >&2
    printf '[ACTUAL]\n' >&2
    cat "$path" >&2
    exit 1
}

step() {
    step_no=$((step_no + 1))
    description=$1
    printf '[STEP] %d %s\n' "$step_no" "$description"
    shift
    printf '[COMMAND]'
    printf ' <%s>' "$@"
    printf '\n'
    set +e
    stdout_file="$output_dir/.stdout"
    stderr_file="$output_dir/.stderr"
    "$@" >"$stdout_file" 2>"$stderr_file"
    rc=$?
    set -e
    printf '[EXIT] %d\n' "$rc"
    print_stream STDOUT "$stdout_file"
    print_stream STDERR "$stderr_file"
    if [ "$rc" -ne 0 ]; then
        printf '[FAIL] %s returned %d; expected exit 0\n' "$description" "$rc" >&2
        exit "$rc"
    fi
    printf '[PASS] %s returned 0\n' "$description"
}

step 'version checks' "$as_bin" --version
step 'assemble fixture' "$as_bin" "$fixture" -o "$object"
step 'read ELF header' "$readelf_bin" -h "$object"
cp "$output_dir/.stdout" "$header"
assert_matches 'Class:[[:space:]]+ELF(32|64)' "$header" \
    'readelf reports an ELF object' 'Class: ELF32 or ELF64'
step 'disassemble fixture' "$objdump_bin" -d "$object"
cp "$output_dir/.stdout" "$disassembly"
assert_matches 'fixture_entry|<fixture_entry>' "$disassembly" \
    'objdump exposes fixture_entry' 'disassembly contains fixture_entry'
step 'list symbols' "$nm_bin" -g "$object"
cp "$output_dir/.stdout" "$symbols"
assert_matches '[[:space:]]fixture_entry$' "$symbols" \
    'nm exposes fixture_entry' 'global symbol table contains fixture_entry'
step 'create archive' "$ar_bin" rcs "$archive" "$object"
step 'link relocatable object' "$ld_bin" -r -o "$linked" "$object"
step 'strip a copy' "$strip_bin" -o "$stripped" "$linked"
step_no=$((step_no + 1))
printf '[STEP] %d negative input control\n' "$step_no"
printf '[COMMAND] <%s> <-h> <%s>\n' "$readelf_bin" "$output_dir/does-not-exist"
set +e
"$readelf_bin" -h "$output_dir/does-not-exist" >"$output_dir/negative.stdout" 2>"$output_dir/negative.stderr"
negative_rc=$?
set -e
printf '[EXIT] %d\n' "$negative_rc"
print_stream STDOUT "$output_dir/negative.stdout"
print_stream STDERR "$output_dir/negative.stderr"
if [ "$negative_rc" -eq 0 ]; then
    printf '[FAIL] readelf accepted a missing input\n' >&2
    printf '[EXPECTED] non-zero exit for a missing file\n' >&2
    printf '[ACTUAL] exit 0\n' >&2
    exit 1
fi
printf '[PASS] invalid input returned non-zero (%d)\n' "$negative_rc"
assert_matches 'does-not-exist.*No such file|No such file.*does-not-exist' \
    "$output_dir/negative.stderr" 'readelf reports the missing input path' \
    'stderr contains does-not-exist and No such file'
printf '[PASS] binutils consumer workflow complete\n'
