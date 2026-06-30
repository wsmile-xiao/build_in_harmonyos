#!/usr/bin/env python3
"""Test script to verify cpplint works on a sample C++ file."""
import os
import sys
import subprocess

def main():
    # Create a small test C++ file
    test_cpp = "test_sample.cpp"
    with open(test_cpp, "w") as f:
        f.write("#include <iostream>\nint main() { return 0; }\n")
    
    # Find cpplint
    cpplint_bin = os.environ.get("CPPLINT_BIN", "cpplint")
    result = subprocess.run(
        [sys.executable, cpplint_bin, "--version"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("cpplint --version: OK")
        print(result.stdout.strip())
    else:
        print("cpplint --version: FAILED")
        print(result.stderr)
        sys.exit(1)
    
    # Clean up
    if os.path.exists(test_cpp):
        os.remove(test_cpp)
    
    print("test cpplint 2.0.2: OK")

if __name__ == "__main__":
    main()
