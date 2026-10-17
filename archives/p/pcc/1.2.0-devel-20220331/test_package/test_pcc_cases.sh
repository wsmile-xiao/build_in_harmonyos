#!/usr/bin/env sh
#
# HarmonyOS-specific end-to-end test for the packaged pcc compiler.
#
# This is NOT an assertion pass over generated text.  Each named case goes
# through the full on-device toolchain chain:
#
#   1. the packaged amd64-linux-pcc compiles a real translation unit
#      (preprocessor + parser + amd64 back end + register allocation) to
#      x86-64 assembly;
#   2. a real assembler (clang -target x86_64-linux-gnu) turns that assembly
#      into an x86-64 object file -- so the assembly must be genuinely valid,
#      not merely text that happens to contain the right mnemonics;
#   3. ld.lld links the object into a real x86-64 ELF executable;
#   4. the ELF header is read back and must say ELF64 / X86-64 / EXEC.
#
# Steps 2-4 are exactly what makes this a test rather than a checklist: if the
# compiler emitted wrong or incomplete code, the assembler or linker fails.
#
# Required environment:
#   PCC_BIN      directory holding the packaged amd64-linux-pcc driver
#   PCC_LIBEXEC  directory holding the packaged ccom/cpp back ends
#   PCC_CASES    directory holding the case_*.c sources
#   PCC_WORK     writable scratch directory
set -eu

: "${PCC_BIN:?PCC_BIN is required}"
: "${PCC_LIBEXEC:?PCC_LIBEXEC is required}"
: "${PCC_CASES:?PCC_CASES is required}"
: "${PCC_WORK:?PCC_WORK is required}"

CC="${PCC_CC:-clang}"
ASM_TARGET="${PCC_ASM_TARGET:-x86_64-linux-gnu}"
LD="${PCC_LD:-ld.lld}"
READELF="${PCC_READELF:-readelf}"

mkdir -p "${PCC_WORK}"
export PATH="${PCC_BIN}:${PCC_LIBEXEC}:${PATH}"
# HarmonyOS mounts /tmp read-only (erofs); keep intermediates in the scratch dir.
export TMPDIR="${PCC_WORK}"

driver="${PCC_BIN}/amd64-linux-pcc"
test -x "${driver}" || { echo "driver not executable: ${driver}" >&2; exit 2; }

cases="arith loop ptr struct"
passed=0
failed=0

for name in ${cases}; do
	src="${PCC_CASES}/case_${name}.c"
	test -f "${src}" || { echo "  case_${name}: source missing" >&2; failed=$((failed + 1)); continue; }

	asm="${PCC_WORK}/case_${name}.s"
	obj="${PCC_WORK}/case_${name}.o"
	elf="${PCC_WORK}/case_${name}.elf"

	if ! "${driver}" -S -o "${asm}" "${src}" 2>"${PCC_WORK}/case_${name}.pcc.log"; then
		echo "  case_${name}: pcc failed to compile" >&2
		tail -n 5 "${PCC_WORK}/case_${name}.pcc.log" >&2
		failed=$((failed + 1)); continue
	fi
	if [ ! -s "${asm}" ]; then
		echo "  case_${name}: pcc produced no assembly" >&2
		failed=$((failed + 1)); continue
	fi

	if ! "${CC}" -target "${ASM_TARGET}" -c "${asm}" -o "${obj}" 2>"${PCC_WORK}/case_${name}.as.log"; then
		echo "  case_${name}: emitted assembly is not valid x86-64 (assembler rejected it)" >&2
		tail -n 5 "${PCC_WORK}/case_${name}.as.log" >&2
		failed=$((failed + 1)); continue
	fi

	if ! "${LD}" -m elf_x86_64 -static -e entry -o "${elf}" "${obj}" 2>"${PCC_WORK}/case_${name}.ld.log"; then
		echo "  case_${name}: link into x86-64 executable failed" >&2
		tail -n 5 "${PCC_WORK}/case_${name}.ld.log" >&2
		failed=$((failed + 1)); continue
	fi

	header=$("${READELF}" -h "${elf}" 2>/dev/null || true)
	case "${header}" in
		*"Class:"*ELF64*) : ;;
		*) echo "  case_${name}: output is not ELF64" >&2; failed=$((failed + 1)); continue ;;
	esac
	case "${header}" in
		*"X86-64"*) : ;;
		*) echo "  case_${name}: output is not an x86-64 machine" >&2; failed=$((failed + 1)); continue ;;
	esac
	case "${header}" in
		*EXEC*) : ;;
		*) echo "  case_${name}: output is not an executable" >&2; failed=$((failed + 1)); continue ;;
	esac

	size=$(wc -c < "${elf}")
	echo "  case_${name}: PASS (pcc -> asm -> ${size}-byte x86-64 ELF executable)"
	passed=$((passed + 1))
done

echo "harmonyos cases: ${passed} passed, ${failed} failed"
test "${failed}" -eq 0
