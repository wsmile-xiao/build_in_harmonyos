#!/bin/sh
# Six test flows and ten semantic assertions for x86_64-elf-grub.
set -euo pipefail

package_root="$1"
assembler="$2"
platform_dir="$package_root/lib/grub/x86_64-efi"
assertions=0

pass_assertion() {
    assertions=$((assertions + 1))
    printf '[assert %d/10] %s\n' "$assertions" "$1"
}

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

printf '[flow 1/6] integration: recognize a valid Multiboot object\n'
"$assembler" -o multiboot.o multiboot.S
test -s multiboot.o || fail "assembler did not create multiboot.o"
pass_assertion "assembled Multiboot object is non-empty"
x86_64-elf-grub-file --is-x86-multiboot multiboot.o
pass_assertion "grub-file recognizes the valid Multiboot object"

printf '[flow 2/6] integration: reject invalid formats\n'
if x86_64-elf-grub-file --is-x86-multiboot grub.cfg; then
    fail "plain grub.cfg was incorrectly recognized as Multiboot"
fi
pass_assertion "grub-file rejects plain text as Multiboot"
if x86_64-elf-grub-file --is-x86_64-efi multiboot.o; then
    fail "Multiboot object was incorrectly recognized as an EFI image"
fi
pass_assertion "grub-file rejects the Multiboot object as EFI"

printf '[flow 3/6] integration: validate a GRUB configuration\n'
x86_64-elf-grub-script-check grub.cfg
pass_assertion "grub-script-check accepts the valid configuration"

printf '[flow 4/6] integration: generate and identify an EFI image\n'
x86_64-elf-grub-mkimage \
    -d "$platform_dir" \
    -O x86_64-efi \
    -o grub-test.efi \
    -p /boot/grub \
    normal echo
test -s grub-test.efi || fail "grub-mkimage produced an empty EFI image"
pass_assertion "grub-mkimage creates a non-empty EFI image"
x86_64-elf-grub-file --is-x86_64-efi grub-test.efi
pass_assertion "grub-file recognizes the generated EFI image"

printf '[flow 5/6] integration: execute the packaged host binary\n'
version_output="$(x86_64-elf-grub-mkimage --version)"
printf '%s\n' "$version_output" | grep -Fq '(GRUB) 2.12' \
    || fail "unexpected grub-mkimage version output"
pass_assertion "packaged host binary runs and reports GRUB 2.12"

printf '[flow 6/6] integration: environment block write/read round trip\n'
environment_file="$PWD/grubenv"
x86_64-elf-grub-editenv "$environment_file" create
test -s "$environment_file" || fail "grub-editenv did not create an environment block"
pass_assertion "grub-editenv creates a non-empty environment block"
x86_64-elf-grub-editenv "$environment_file" set harmony_pc=verified
x86_64-elf-grub-editenv "$environment_file" list \
    | grep -Fxq 'harmony_pc=verified' \
    || fail "grub-editenv did not persist the expected value"
pass_assertion "grub-editenv persists and reads the expected value"

test "$assertions" -eq 10 || fail "expected 10 assertions, got $assertions"
printf 'PASS: 6 test flows, 10 assertions\n'
