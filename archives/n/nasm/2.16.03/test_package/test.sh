#!/bin/sh
set -eu

nasm_bin=$1
ndisasm_bin=$2
flat_input=$3
flat_output=$4
disassembly=$5
elf_input=$6
elf_output=$7

"$nasm_bin" --version
"$ndisasm_bin" -v
"$nasm_bin" -f bin "$flat_input" -o "$flat_output"
"$ndisasm_bin" -b 16 "$flat_output" > "$disassembly"
"$nasm_bin" -f elf64 "$elf_input" -o "$elf_output"
