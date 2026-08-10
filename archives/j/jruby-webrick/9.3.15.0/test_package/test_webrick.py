#!/usr/bin/env python3
"""
test_webrick.py — Validates packaged WEBrick .rb files.

Checks:
  1. webrick.rb exists in the package and is non-empty
  2. webrick.rb contains 'module WEBrick' — the main module declaration
  3. webrick/server.rb exists and contains 'class SimpleServer' or 'class GenericServer'
  4. webrick/httpserver.rb exists and contains 'class HTTPServer'
  5. webrick/httprequest.rb exists and contains 'class HTTPRequest'
  6. webrick/httpresponse.rb exists and contains 'class HTTPResponse'
  7. webrick/config.rb exists and contains 'module Config'
  8. Count total .rb files in the webrick/ directory (should be >= 15)
  9. webrick/ssl.rb exists (SSL support)
 10. webrick/httpproxy.rb exists (proxy support)

Exit 0 on success, non-zero on failure with a clear error message.
"""

import os
import sys


def check_file_exists(filepath, label):
    if not os.path.isfile(filepath):
        print(f"FAIL: {label} — file not found: {filepath}")
        return False
    return True


def check_file_nonempty(filepath, label):
    if os.path.getsize(filepath) == 0:
        print(f"FAIL: {label} — file is empty: {filepath}")
        return False
    return True


def check_content_contains(filepath, pattern, label):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"FAIL: {label} — cannot read file {filepath}: {e}")
        return False

    if pattern not in content:
        print(f"FAIL: {label} — file {filepath} does not contain pattern: {pattern!r}")
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: test_webrick.py <package_folder>")
        sys.exit(1)

    package_folder = sys.argv[1]
    stdlib_dir = os.path.join(package_folder, "lib", "ruby", "stdlib")
    webrick_dir = os.path.join(stdlib_dir, "webrick")

    passed = 0
    failed = 0

    # Check 1: webrick.rb exists and is non-empty
    webrick_main = os.path.join(stdlib_dir, "webrick.rb")
    if not check_file_exists(webrick_main, "Check 1"):
        failed += 1
    elif not check_file_nonempty(webrick_main, "Check 1"):
        failed += 1
    else:
        passed += 1
        print("PASS: Check 1 — webrick.rb exists and is non-empty")

    # Check 2: webrick.rb contains 'module WEBrick'
    if not check_file_exists(webrick_main, "Check 2"):
        failed += 1
    elif not check_content_contains(webrick_main, "module WEBrick", "Check 2"):
        failed += 1
    else:
        passed += 1
        print("PASS: Check 2 — webrick.rb contains 'module WEBrick'")

    # Check 3: webrick/server.rb contains 'class SimpleServer' or 'class GenericServer'
    server_rb = os.path.join(webrick_dir, "server.rb")
    if not check_file_exists(server_rb, "Check 3"):
        failed += 1
    else:
        try:
            with open(server_rb, "r", encoding="utf-8") as f:
                content = f.read()
            if "class SimpleServer" in content or "class GenericServer" in content:
                passed += 1
                print("PASS: Check 3 — webrick/server.rb contains a Server class")
            else:
                print(f"FAIL: Check 3 — webrick/server.rb does not contain 'class SimpleServer' or 'class GenericServer'")
                failed += 1
        except Exception as e:
            print(f"FAIL: Check 3 — cannot read {server_rb}: {e}")
            failed += 1

    # Check 4: webrick/httpserver.rb contains 'class HTTPServer'
    httpserver_rb = os.path.join(webrick_dir, "httpserver.rb")
    if not check_file_exists(httpserver_rb, "Check 4"):
        failed += 1
    elif not check_content_contains(httpserver_rb, "class HTTPServer", "Check 4"):
        failed += 1
    else:
        passed += 1
        print("PASS: Check 4 — webrick/httpserver.rb contains 'class HTTPServer'")

    # Check 5: webrick/httprequest.rb contains 'class HTTPRequest'
    httprequest_rb = os.path.join(webrick_dir, "httprequest.rb")
    if not check_file_exists(httprequest_rb, "Check 5"):
        failed += 1
    elif not check_content_contains(httprequest_rb, "class HTTPRequest", "Check 5"):
        failed += 1
    else:
        passed += 1
        print("PASS: Check 5 — webrick/httprequest.rb contains 'class HTTPRequest'")

    # Check 6: webrick/httpresponse.rb contains 'class HTTPResponse'
    httpresponse_rb = os.path.join(webrick_dir, "httpresponse.rb")
    if not check_file_exists(httpresponse_rb, "Check 6"):
        failed += 1
    elif not check_content_contains(httpresponse_rb, "class HTTPResponse", "Check 6"):
        failed += 1
    else:
        passed += 1
        print("PASS: Check 6 — webrick/httpresponse.rb contains 'class HTTPResponse'")

    # Check 7: webrick/config.rb contains 'module Config'
    config_rb = os.path.join(webrick_dir, "config.rb")
    if not check_file_exists(config_rb, "Check 7"):
        failed += 1
    elif not check_content_contains(config_rb, "module Config", "Check 7"):
        failed += 1
    else:
        passed += 1
        print("PASS: Check 7 — webrick/config.rb contains 'module Config'")

    # Check 8: Count total .rb files in webrick/ directory (should be >= 15)
    rb_count = 0
    if os.path.isdir(webrick_dir):
        for root, dirs, files in os.walk(webrick_dir):
            for f in files:
                if f.endswith(".rb"):
                    rb_count += 1
    if rb_count >= 15:
        passed += 1
        print(f"PASS: Check 8 — webrick/ directory has {rb_count} .rb files (>= 15)")
    else:
        failed += 1
        print(f"FAIL: Check 8 — webrick/ directory has {rb_count} .rb files (< 15)")

    # Check 9: webrick/ssl.rb exists (SSL support)
    ssl_rb = os.path.join(webrick_dir, "ssl.rb")
    if not check_file_exists(ssl_rb, "Check 9"):
        failed += 1
    else:
        passed += 1
        print("PASS: Check 9 — webrick/ssl.rb exists (SSL support)")

    # Check 10: webrick/httpproxy.rb exists (proxy support)
    httpproxy_rb = os.path.join(webrick_dir, "httpproxy.rb")
    if not check_file_exists(httpproxy_rb, "Check 10"):
        failed += 1
    else:
        passed += 1
        print("PASS: Check 10 — webrick/httpproxy.rb exists (proxy support)")

    print(f"\nResults: {passed} passed, {failed} failed out of {passed + failed} checks")
    if failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
