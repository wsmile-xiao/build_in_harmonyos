#!/usr/bin/env bash
# test_package/test.sh - offline checks against the packaged kubeaudit binary.
# 5 universal checks (version embed, help, manifest-mode audit positive and
# negative, autofix) + 2 OHOS-specific checks (--ohos: OHOS ELF signature and
# static linking of the CGO_ENABLED=0 build). No network access.
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: $0 <path-to-kubeaudit> [--ohos]" >&2
    exit 2
fi

kubeaudit_bin="$1"
ohos_mode="false"
if [ "${2:-}" = "--ohos" ]; then
    ohos_mode="true"
fi

script_dir="$(cd "$(dirname "$0")" && pwd)"
bad_yaml="$script_dir/bad.yml"
good_yaml="$script_dir/good.yml"

if [ ! -x "$kubeaudit_bin" ]; then
    echo "kubeaudit binary not found or not executable: $kubeaudit_bin" >&2
    exit 1
fi

# 1. version flag prints the go:embed'ed VERSION (works under the OHOS build)
version_output="$("$kubeaudit_bin" version)"
printf '%s\n' "$version_output" | grep -F "0.22.2" >/dev/null
echo "CHECK-OK: version prints 0.22.2"

# 2. help exits zero
"$kubeaudit_bin" --help >/dev/null
echo "CHECK-OK: help exits zero"

# 3. manifest-mode audit flags the known PrivilegedTrue error (offline, exit
#    code 2 = default --exitcode for error-severity results)
audit_rc=0
audit_output="$("$kubeaudit_bin" privileged -f "$bad_yaml" 2>&1)" || audit_rc=$?
printf '%s\n' "$audit_output" | grep -F "PrivilegedTrue" >/dev/null
if [ "$audit_rc" -ne 2 ]; then
    echo "expected exit code 2 for error-severity audit result, got: $audit_rc" >&2
    exit 1
fi
echo "CHECK-OK: audit reports PrivilegedTrue and exits 2"

# 4. manifest-mode audit of a clean manifest exits 0 (no error-severity results)
clean_rc=0
clean_output="$("$kubeaudit_bin" privileged -f "$good_yaml" 2>&1)" || clean_rc=$?
if [ "$clean_rc" -ne 0 ]; then
    echo "expected exit code 0 for clean manifest, got: $clean_rc" >&2
    printf '%s\n' "$clean_output" >&2
    exit 1
fi
printf '%s\n' "$clean_output" | grep -F "PrivilegedTrue" >/dev/null && {
    echo "clean manifest unexpectedly flagged PrivilegedTrue" >&2
    exit 1
}
echo "CHECK-OK: clean manifest audits clean and exits 0"

# 5. autofix rewrites privileged: true to false in manifest mode
fixed_yaml="$(dirname "$bad_yaml")/bad-fixed.yml"
rm -f "$fixed_yaml"
"$kubeaudit_bin" autofix -f "$bad_yaml" -o "$fixed_yaml" >/dev/null
grep -F "privileged: false" "$fixed_yaml" >/dev/null
rm -f "$fixed_yaml"
echo "CHECK-OK: autofix rewrites privileged to false"

if [ "$ohos_mode" = "true" ]; then
    # 6. OHOS adaptation point: binary carries the mandatory OHOS ELF
    #    signature section added by binary-sign-tool (unsigned ELF is
    #    refused by execve on HarmonyOS).
    if grep -qa -e ".codesign" -e ".note.ohos" "$kubeaudit_bin"; then
        echo "CHECK-OK: binary carries OHOS signature section"
    else
        echo "binary lacks OHOS signature section (.codesign/.note.ohos)" >&2
        exit 1
    fi

    # 7. OHOS adaptation point: CGO_ENABLED=0 build is statically linked -
    #    no PT_INTERP and no DT_NEEDED, i.e. no glibc/musl dynamic coupling.
    readelf_bin=""
    for candidate in readelf llvm-readelf; do
        if command -v "$candidate" >/dev/null 2>&1; then
            readelf_bin="$candidate"
            break
        fi
    done
    if [ -z "$readelf_bin" ]; then
        echo "no readelf/llvm-readelf on PATH for static-linking check" >&2
        exit 1
    fi
    if "$readelf_bin" -l "$kubeaudit_bin" | grep -q "INTERP"; then
        echo "binary has PT_INTERP - not statically linked" >&2
        exit 1
    fi
    if "$readelf_bin" -d "$kubeaudit_bin" | grep -q "NEEDED"; then
        echo "binary has DT_NEEDED entries - not statically linked" >&2
        exit 1
    fi
    echo "CHECK-OK: binary is statically linked (no PT_INTERP, no DT_NEEDED)"
fi

if [ "$ohos_mode" = "true" ]; then
    echo "All 7 kubeaudit test_package checks passed."
else
    echo "All 5 kubeaudit test_package checks passed."
fi
