#!/usr/bin/env python3
import json
import os
import subprocess
import sys

from gsan.main import clean_domains, extract_subdomains, parse_domain


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def run_cli(*args):
    command = [sys.executable, "-m", "gsan.main"] if os.name == "nt" else ["gsan"]
    return subprocess.run([*command, *args], capture_output=True, text=True, check=False)


# Mock getpeercert() dict — no offline certificate parsing needed
mock_cert = {
    "subject": (((("commonName", "example.com"),),),),
    "subjectAltName": (
        ("DNS", "*.example.com"),
        ("DNS", "www.example.com"),
        ("DNS", "api.example.com"),
        ("IP Address", "127.0.0.1"),
    ),
}

subdomains = extract_subdomains(mock_cert)
check("*.example.com" in subdomains, "extracts DNS SAN from certificate dict")
check("127.0.0.1" in subdomains, "extracts IP SAN from certificate dict")
check(clean_domains(["*.www.example.com", "www.example.com", "api.example.com"]) == ["api.example.com", "example.com"], "cleans prefixes and deduplicates SAN values")
check(parse_domain("example.com:8443") == ("example.com", 8443), "parses hostname and explicit port")
check(parse_domain("example.com") == ("example.com", 443), "uses default TLS port")
check(parse_domain("[::1]:9443") == ("::1", 9443), "parses bracketed IPv6 endpoint")
version = run_cli("--version")
check(version.returncode == 0 and version.stdout.strip() == "gsan 5.0.0", "reports package version")
help_result = run_cli("--help")
check(help_result.returncode == 0 and "--format" in help_result.stdout, "prints CLI help")
failure = run_cli("127.0.0.1:1", "--timeout", "0.1", "--format", "json")
check(failure.returncode == 0, "reports connection failure without crashing")
payload = json.loads(failure.stdout)
check(payload["failed_domains"] == ["127.0.0.1"], "reports failed domain in JSON output")
print("10 assertions passed")
