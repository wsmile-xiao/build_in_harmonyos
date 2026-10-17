#!/usr/bin/env python3
"""Test verification script for ca-certificates.

Verifies that the ca-certificates package contains the expected
Mozilla CA certificate bundle with valid PEM-format certificates
and the update-ca-certificates tool.

Usage: python3 test_verify.py <package_root>
"""
import os
import sys
import glob


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_verify.py <package_root>")
        sys.exit(1)

    pkg_root = sys.argv[1]
    cert_dir = os.path.join(pkg_root, "share", "ca-certificates", "mozilla")
    sbin_dir = os.path.join(pkg_root, "sbin")

    # Check certificate directory exists
    assert os.path.isdir(cert_dir), f"Certificate directory not found: {cert_dir}"
    print(f"Certificate directory: {cert_dir}")

    # Count certificates
    crt_files = glob.glob(os.path.join(cert_dir, "*.crt"))
    cert_count = len(crt_files)
    print(f"Certificate count: {cert_count}")
    assert cert_count >= 100, f"Expected >=100 certificates, got {cert_count}"

    # Check PEM format of first certificate
    with open(crt_files[0], "r") as f:
        content = f.read()
    assert "BEGIN CERTIFICATE" in content, "Certificate not in PEM format"
    assert "END CERTIFICATE" in content, "Certificate not in PEM format"
    print(f"PEM format verified: {os.path.basename(crt_files[0])}")

    # Check update-ca-certificates exists
    update_script = os.path.join(sbin_dir, "update-ca-certificates")
    assert os.path.isfile(update_script), f"update-ca-certificates not found: {update_script}"
    print(f"update-ca-certificates found: {update_script}")

    print("All tests passed!")


if __name__ == "__main__":
    main()
