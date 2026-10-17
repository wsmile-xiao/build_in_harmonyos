#!/bin/sh
# Consumer smoke: the packaged server binary must execute and self-report.
# (Upstream prints the version banner and exits 1; assert on the output.)
out=$(yaskkserv_simple --version 2>&1)
echo "$out" | grep -q "version 1.1.1" || {
    echo "unexpected version output: $out"
    exit 1
}
echo "yaskkserv consumer test passed: 1 assertion (server --version self-report)"
