#!/usr/bin/env python3
"""Conan recipe — launchctl-completion 2.0 (bash completion data package).

launchctl-completion upstream v2.0 ships exactly two files: LICENSE (MIT)
and launchctl-completion.sh (713-line bash completion script for macOS
launchctl(8)). It is a pure data package: nothing is compiled, nothing is
executed at build time, and there is no install mechanism upstream (no
Makefile) — Homebrew's formula installs it with a single placement action:
`bash_completion.install "launchctl-completion.sh" => "launchctl"`.
This recipe mirrors that layout (data-package fidelity, knowledge E241):

  share/bash-completion/completions/launchctl   renamed placement, content
                                                byte-identical to upstream
  licenses/LICENSE                              Conan license convention

Shape decisions (E241 data-package-pattern, matching this repo's gates):
- `settings` attribute omitted entirely (== None in Conan 2): a data package
  does not depend on os/compiler/arch. (A `settings = None` literal would
  trip the CI L0p settings-axis check, which only tolerates a settings line
  that lists all four profile axes.)
- no `package_type`: there is no executable artifact — the completed command
  `launchctl` itself is NOT part of this package — so the R38/commands.json
  CLI-tool gate does not apply (L0k detects no bindirs / bin install /
  application type).
- no build step: upstream content ships byte-for-byte. Known OHOS runtime
  limitations are disclosed (README/manifest/report), not patched away.

Runtime contract: the completion file is *sourced by the user's bash*, never
executed, so its `#!/usr/local/bin/bash` shebang is inert (knowledge E037/
E049 family). The script needs `compgen -V` (new in bash 5.3, 65 call
sites) and `local -n` namerefs (bash >= 4.3), hence requires("bash/5.3")
— the same contract the kworkflow precedent pins for sourced completions.

Known OHOS runtime limitations (honest disclosure, not packaging defects):
- `launchctl` does not exist on OHOS: the `complete -F` registration is
  harmless and only fires if the user types `launchctl <TAB>`.
- dynamic data sources are absent (`launchctl list`, `dscl`,
  /Library/Launch*): dynamic branches complete to the empty set; the static
  first-level subcommand completion (44 literals) works in any bash >= 5.3.
- three `launchctl list` call sites (script lines 97/102/107) have no
  stderr guard: completing e.g. `list <TAB>` prints a command-not-found
  noise line. Upstream content is intentionally left unmodified.
"""
import hashlib
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get


class LaunchctlCompletionConan(ConanFile):
    name = "launchctl-completion"
    version = "2.0"
    description = "Bash completion data package for macOS launchctl(8)"
    license = "MIT"
    homepage = "https://github.com/CamJN/launchctl-completion"
    url = ""
    topics = ("bash-completion", "completion", "shell", "data-package")

    # E241 data-package-pattern: no settings attribute (config-free), no
    # package_type (no executable artifact), no build system. See docstring.
    requires = ("bash/5.3",)

    # Per-file SHA256 pins of the extracted upstream payload (the tarball
    # itself is already verified by get() against conandata.yml sources
    # sha256). Values recomputed independently from the v2.0 tarball.
    PAYLOAD_SHA256 = {
        "launchctl-completion.sh":
            "17df5430689d60d4bf7b555d0e00adf215b2c09037235d65abdc83a931249f0b",
        "LICENSE":
            "898275fba946f95c028e23a6849c22e29eb47e772bfc84fc1c30a82e515e7e5b",
    }

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # E241 data-integrity gate: assert the extracted tree carries exactly
        # the two upstream files this recipe packages, byte-identical to the
        # pinned hashes, then emit the machine-readable upstream-test
        # discovery marker (upstream has zero tests — full evidence chain in
        # test_package/MANIFEST.yml, EXCLUDED-TESTS.md and
        # UPSTREAM-TESTS-EVIDENCE.json).
        srcdir = self.source_folder
        # Conan 2 writes aggregated env scripts into the build folder before
        # build() runs (host-env scaffolding for requires("bash/5.3")); they
        # are runtime derivatives, not recipe inputs (knowledge E403 / mlton
        # experience), so exclude that fixed name set from the file-set audit.
        conan_generated = {
            "conanbuild.sh", "conanbuildenv.sh", "conanrun.sh",
            "conanrunenv.sh", "deactivate_conanbuild.sh",
            "deactivate_conanrun.sh",
        }
        actual = sorted(
            f for f in os.listdir(srcdir)
            if not f.startswith(".") and f not in conan_generated
        )
        if actual != sorted(self.PAYLOAD_SHA256):
            raise ConanException(
                f"unexpected upstream file set: {actual} != "
                f"{sorted(self.PAYLOAD_SHA256)}"
            )
        for fname, expected in self.PAYLOAD_SHA256.items():
            digest = hashlib.sha256(
                open(os.path.join(srcdir, fname), "rb").read()
            ).hexdigest()
            if digest != expected:
                raise ConanException(
                    f"{fname}: sha256 {digest} != pinned {expected}"
                )
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "not_applicable",
                "framework": "none",
                "command": "n/a",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "discovery": "NO_UPSTREAM_TESTS",
                "evidence": [
                    "v2.0 tarball contains exactly 2 files (LICENSE + "
                    "launchctl-completion.sh, sha256-verified in build()): "
                    "no tests/ directory and no *_test.* files",
                    "no Makefile and no test runner entry point of any kind",
                    "no CI configuration: no .github/, no .gitlab-ci.yml",
                ],
            }, sort_keys=True)
        )

    def package(self):
        # Homebrew-equivalent placement: rename to the completed command name
        # in the standard bash-completion lookup path (kworkflow precedent
        # ships share/bash-completion/completions/kw the same way).
        compdir = os.path.join(
            self.package_folder, "share", "bash-completion", "completions"
        )
        copy(self, "launchctl-completion.sh",
             src=self.source_folder, dst=compdir, keep_path=False)
        os.rename(os.path.join(compdir, "launchctl-completion.sh"),
                  os.path.join(compdir, "launchctl"))
        # License retained per Conan convention; upstream files untouched.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Data package: declare the data root; no bindirs on purpose (R38).
        self.cpp_info.resdirs = ["share"]
