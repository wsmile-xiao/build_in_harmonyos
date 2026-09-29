#!/bin/sh
# Consumer smoke test for kubeadm (k8s.io/kubernetes cmd/kubeadm).
# $1 = absolute path to the kubeadm binary.
# Asserts the binary runs on OHOS and reports the injected v1.36.2 version
# (gitVersion is injected via go build -ldflags in the recipe).
set -eu

KUBEADM="$1"

echo "== kubeadm version =="
out=$("$KUBEADM" version)
echo "$out"

case "$out" in
    *v1.36.2*)
        echo "HMBS_KUBEADM_VERSION_OK"
        ;;
    *)
        echo "HMBS_KUBEADM_VERSION_FAIL: expected v1.36.2 in version output" >&2
        exit 1
        ;;
esac
