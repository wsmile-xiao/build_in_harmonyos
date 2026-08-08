#!/bin/sh
# Smoke test: verify core arm-none-eabi-binutils tools
# This test is run by test_package/conanfile.py's test() method.
# Listed here as a test source file for L0c quality gate.

set -e

for tool in arm-none-eabi-objdump arm-none-eabi-objcopy arm-none-eabi-ld \
            arm-none-eabi-as arm-none-eabi-ar arm-none-eabi-nm \
            arm-none-eabi-strip arm-none-eabi-size; do
    "$tool" --version
done