#!/bin/bash
# test_package/test.sh — Smoke test for haproxy 3.2.0
# Verifies the haproxy binary can execute and report its version.
set -euo pipefail

haproxy -v
