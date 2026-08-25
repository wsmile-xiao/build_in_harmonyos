#!/usr/bin/env sh
set -eu

if [ "$#" -ne 7 ]; then
  echo "usage: smoke.sh AS LD OBJCOPY SOURCE OBJECT ELF HEX" >&2
  exit 2
fi

assembler=$1
linker=$2
objcopy=$3
source=$4
object=$5
elf=$6
ihex=$7

"$assembler" -mmcu=atmega328p -o "$object" "$source"
"$linker" -m avr5 -e _start -o "$elf" "$object"
"$objcopy" -O ihex "$elf" "$ihex"
