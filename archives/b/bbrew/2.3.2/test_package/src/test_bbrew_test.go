// test_package/src/test_bbrew_test.go
//
// L1/L2 smoke test for the bbrew application package.
//
// This test exercises the actual installed `bbrew` binary by running it
// with the `--version` flag. The binary's --version handler reads the
// `services.AppVersion` symbol that is baked in at link time via
// `-ldflags -X bbrew/internal/services.AppVersion=2.3.2`, so a successful
// run with the expected version string proves:
//   1. The Go binary was cross-compiled correctly (R34 substantive test).
//   2. The PIE (ET_DYN) binary is loadable on HarmonyOS HMDFS.
//   3. The conanfile.py package() step installed the binary to bin/.
//
// Run: go test ./...
package main

import (
	"os"
	"os/exec"
	"strings"
	"testing"
)

func TestBbrewVersion(t *testing.T) {
	// Locate the installed bbrew binary via the BBREW_BIN env var
	// (set by test_package/conanfile.py) or fall back to PATH lookup.
	bin := os.Getenv("BBREW_BIN")
	if bin == "" {
		var err error
		bin, err = exec.LookPath("bbrew")
		if err != nil {
			// R34: the test must genuinely depend on the packaged bbrew
			// binary. If it is missing (BBREW_BIN unset and not on PATH),
			// fail hard instead of skipping — mirroring test_bbrew.sh
			// (exit 1) and test_package/conanfile.py (AssertionError), so
			// CI L1e sabotage (bin/ removed) is detected by go test too.
			t.Fatalf("bbrew binary not found (BBREW_BIN unset and not on PATH): %v", err)
		}
	}

	out, err := exec.Command(bin, "--version").Output()
	if err != nil {
		t.Fatalf("bbrew --version failed: %v\noutput: %s", err, out)
	}
	got := strings.TrimSpace(string(out))
	// R9/R34: reject placeholder artifacts. conanfile.py._build_placeholder()
	// (used when the Go toolchain is unavailable) emits a "[PLACEHOLDER]"
	// marker; a real CI build must never ship or pass tests on that stub.
	if strings.Contains(got, "[PLACEHOLDER]") {
		t.Fatalf("bbrew --version = %q: placeholder binary detected (Go toolchain unavailable on runner), genuine Go build required (R9: no fake pass)", got)
	}
	if !strings.Contains(got, "2.3.2") {
		t.Errorf("bbrew --version = %q, want version string containing 2.3.2", got)
	}
}

func TestBbrewHelpExitCode(t *testing.T) {
	bin := os.Getenv("BBREW_BIN")
	if bin == "" {
		var err error
		bin, err = exec.LookPath("bbrew")
		if err != nil {
			// R34: fail hard when the packaged binary is missing (see
			// TestBbrewVersion) instead of skipping.
			t.Fatalf("bbrew binary not found: %v", err)
		}
	}
	// bbrew -h should exit 0 (flag.Usage prints help then the flag package
	// returns ErrHelp which main.go does not treat as fatal).
	out, err := exec.Command(bin, "-h").CombinedOutput()
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			t.Errorf("bbrew -h exited with %d, expected 0", exitErr.ExitCode())
		} else {
			t.Errorf("bbrew -h failed to start: %v", err)
		}
	}
	// R9/R34: reject placeholder artifacts here too (the placeholder stub
	// also exits 0 on -h, so the exit-code check alone cannot catch it).
	if strings.Contains(string(out), "[PLACEHOLDER]") {
		t.Fatalf("bbrew -h = %q: placeholder binary detected, genuine Go build required (R9: no fake pass)", out)
	}
}
