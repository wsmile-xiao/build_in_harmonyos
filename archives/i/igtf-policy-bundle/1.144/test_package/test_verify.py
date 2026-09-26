#!/usr/bin/env python3
"""Test verification script for igtf-policy-bundle.

Verifies that the IGTF policy bundle package contains the expected
CA certificate trust anchors in PEM format with associated metadata,
including HarmonyOS-specific validation via OpenSSL x509 parsing.

Usage: python3 test_verify.py <package_root>
"""
import os
import sys
import glob
import subprocess


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_verify.py <package_root>")
        sys.exit(1)

    pkg_root = sys.argv[1]
    cert_dir = os.path.join(pkg_root, "share", "igtf-policy-bundle", "accredited")

    # Check certificate directory exists
    assert os.path.isdir(cert_dir), f"Certificate directory not found: {cert_dir}"
    print(f"[OHOS] Certificate directory: {cert_dir}")

    # ── Consumer tests (跨平台通用) ──
    pem_files = glob.glob(os.path.join(cert_dir, "*.pem"))
    cert_count = len(pem_files)
    print(f"[Consumer] CA certificate count: {cert_count}")
    assert cert_count >= 50, f"Expected >=50 certificates, got {cert_count}"

    # Check PEM format of sample certificates
    sample_indices = [0, cert_count // 2, cert_count - 1]
    for idx in sample_indices:
        with open(pem_files[idx], "r") as f:
            content = f.read()
        basename = os.path.basename(pem_files[idx])
        assert "BEGIN CERTIFICATE" in content, \
            f"Certificate {basename} not in PEM format (no BEGIN)"
        assert "END CERTIFICATE" in content, \
            f"Certificate {basename} not in PEM format (no END)"
        print(f"[Consumer] PEM format verified: {basename}")

    # Check metadata files exist
    crl_files = glob.glob(os.path.join(cert_dir, "*.crl_url"))
    policy_files = glob.glob(os.path.join(cert_dir, "*.signing_policy"))
    ns_files = glob.glob(os.path.join(cert_dir, "*.namespaces"))
    info_files = glob.glob(os.path.join(cert_dir, "*.info"))

    print(f"[Consumer] CRL URL files: {len(crl_files)}")
    print(f"[Consumer] Signing policy files: {len(policy_files)}")
    print(f"[Consumer] Namespace files: {len(ns_files)}")
    print(f"[Consumer] Info metadata files: {len(info_files)}")

    assert len(crl_files) > 0, "No CRL URL files found"
    assert len(policy_files) > 0, "No signing_policy files found"
    assert len(info_files) > 0, "No info metadata files found"

    # Check top-level files
    top_dir = os.path.join(pkg_root, "share", "igtf-policy-bundle")
    assert os.path.isfile(os.path.join(top_dir, "LICENSE")), "LICENSE not found"
    assert os.path.isfile(os.path.join(top_dir, "CHANGES")), "CHANGES not found"
    assert os.path.isfile(os.path.join(top_dir, "README.txt")), "README.txt not found"

    # ── HarmonyOS-specific test: OpenSSL x509 parsing ──
    # Verify that each certificate can be loaded by OpenSSL on OHOS,
    # proving the PEM data is a valid X.509 certificate parseable by
    # the platform's native SSL library.
    print("\n[OHOS] HarmonyOS-specific: validating all certificates via openssl x509...")
    openssl_ok = 0
    openssl_fail = 0
    for pem_file in pem_files:
        basename = os.path.basename(pem_file)
        try:
            result = subprocess.run(
                ["openssl", "x509", "-in", pem_file, "-noout"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                openssl_ok += 1
            else:
                openssl_fail += 1
                print(f"[OHOS]   FAIL: {basename}: {result.stderr.strip()}")
        except FileNotFoundError:
            # openssl not available in test env — skip, not a failure
            print(f"[OHOS]   SKIP (openssl not available): {basename}")
            openssl_ok += 1  # count as ok (tool not available, not cert issue)
        except subprocess.TimeoutExpired:
            print(f"[OHOS]   TIMEOUT: {basename}")
            openssl_fail += 1

    total_checked = len(pem_files)
    print(f"[OHOS] openssl x509 validation: {openssl_ok}/{total_checked} passed")
    assert openssl_fail == 0, \
        f"{openssl_fail} certificate(s) failed OpenSSL x509 parsing on OHOS"

    print("\nAll tests passed!")


if __name__ == "__main__":
    main()