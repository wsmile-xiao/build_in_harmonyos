#!/usr/bin/env python3
"""Conan recipe -- debuerreotype 0.16 (pure Bash rootfs builder scripts).

debuerreotype/debuerreotype: reproducible, snapshot-based Debian rootfs
builder (especially for Docker). Pure Bash application, no C compilation:
a set of self-contained scripts in scripts/ whose runtime deps are
bash/getopt/debootstrap-like tooling on the operator host. This recipe only
packages the scripts with VERSION and docs, and runs syntax + smoke
self-checks as verification (no network, no debootstrap, no Docker).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


def _find_bash():
    # Strict bash resolution. The scripts under test are Bash (arrays,
    # [[ ]], pipefail); POSIX sh cannot parse them, so this helper returns
    # a real bash path or None, NEVER a plain sh.
    candidates = [
        os.environ.get("BASH"),
        shutil.which("bash"),
        "/bin/bash",
        "/usr/bin/bash",
        "/usr/local/bin/bash",
        "/storage/Users/currentUser/usr/local/bin/bash",
        "/system/bin/bash",
        os.environ.get("CONFIG_SHELL"),
        "/data/service/hnp/bin/bash",
    ]
    for cand in candidates:
        if cand and os.path.basename(cand).find("bash") >= 0 \
                and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


class DebuerreotypeConan(ConanFile):
    name = "debuerreotype"
    version = "0.16"
    description = "Reproducible, snapshot-based Debian rootfs builder (Bash scripts)"
    license = "MIT"
    homepage = "https://github.com/debuerreotype/debuerreotype"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure Bash scripts, no compilation. Preferred self-checks:
        #   1) bash -n syntax check over every scripts/debuerreotype-* entry
        #   2) debuerreotype-version smoke: really executes the script
        #      (sources .constants.sh, runs getopt option parsing, reads
        #      VERSION) and asserts the output contains 0.16.
        # Preflight workers may ship only /bin/sh without bash. In that
        # case do NOT fail the build: fall back to portable Python checks
        # (presence, VERSION content, shebang, key-function grep) so the
        # pure-script payload can still be packaged. Full bash verification
        # runs whenever bash exists (test_package + hosts with bash).
        bash = _find_bash()
        src = self.source_folder
        if bash:
            scripts = os.path.join(src, "scripts")
            self.run('cd "%s" && "%s" -n scripts/debuerreotype-version' % (src, bash))
            self.run(
                'cd "%s" && for s in scripts/debuerreotype-*; do "%s" -n "$s"; done' % (src, bash)
            )
            self.run(
                'cd "%s" && PWD="%s" "%s" scripts/debuerreotype-version 2>&1 | grep -q "0.16"'
                % (src, scripts, bash)
            )
            return
        self.output.warning(
            "bash not found on build worker; running portable fallback "
            "checks instead of bash -n/smoke (packaging still valid)"
        )
        scripts_dir = os.path.join(src, "scripts")
        entries = [f for f in os.listdir(scripts_dir) if f.startswith("debuerreotype-")]
        if not entries:
            raise ConanException("fallback check failed: no scripts/debuerreotype-* entries found")
        version_path = os.path.join(src, "VERSION")
        with open(version_path, "r", encoding="utf-8", errors="strict") as f:
            version_content = f.read().strip()
        if "0.16" not in version_content:
            raise ConanException(
                "fallback check failed: VERSION does not contain 0.16: %r" % version_content
            )
        for entry in entries:
            path = os.path.join(scripts_dir, entry)
            if os.path.getsize(path) == 0:
                raise ConanException("fallback check failed: empty script %s" % entry)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read(4096).splitlines()
            if not lines or "bash" not in lines[0]:
                raise ConanException("fallback check failed: %s missing bash shebang" % entry)
        version_script = os.path.join(scripts_dir, "debuerreotype-version")
        with open(version_script, "r", encoding="utf-8", errors="replace") as f:
            version_src = f.read()
        # debuerreotype-version is a small dispatcher: it sources
        # .constants.sh and calls _version (defined there, reading
        # scriptsDir/../VERSION). Assert the call here and the lookup
        # inside .constants.sh separately.
        if "_version" not in version_src:
            raise ConanException(
                "fallback check failed: debuerreotype-version missing _version call"
            )
        constants = os.path.join(scripts_dir, ".constants.sh")
        with open(constants, "r", encoding="utf-8", errors="replace") as f:
            constants_src = f.read()
        if "VERSION" not in constants_src or "_version()" not in constants_src:
            raise ConanException(
                "fallback check failed: .constants.sh missing VERSION lookup"
            )

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        # Main entry scripts plus the dot-helper files they source
        # (.constants.sh, .apt-version.sh, .snapshot-url.sh, etc.).
        copy(self, "debuerreotype-*", src=os.path.join(src, "scripts"), dst=bindir)
        copy(self, ".*.sh", src=os.path.join(src, "scripts"), dst=bindir)
        copy(self, ".slimify-excludes", src=os.path.join(src, "scripts"), dst=bindir)
        copy(self, ".slimify-includes", src=os.path.join(src, "scripts"), dst=bindir)
        copy(self, ".tar-exclude", src=os.path.join(src, "scripts"), dst=bindir)
        for fname in os.listdir(bindir):
            path = os.path.join(bindir, fname)
            if os.path.isfile(path) and fname.startswith("debuerreotype-"):
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    # HMBS workers may expose HMBS_CAP_CHMOD=0 (chmod
                    # unsupported / read-only overlay). Best effort only;
                    # entry scripts already carry exec bits from the tarball
                    # and are invoked via an explicit bash interpreter.
                    pass
        # VERSION sits next to scripts/ upstream; _version() reads
        # "$scriptsDir/../VERSION", so place it at the package root
        # (bin/../VERSION) to keep the installed layout working.
        copy(self, "VERSION", src=src, dst=self.package_folder, keep_path=False)
        copy(self, "LICENSE", src=src, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        doc = os.path.join(self.package_folder, "share", "doc", "debuerreotype")
        copy(self, "README.md", src=src, dst=doc, keep_path=False)
        copy(self, "Dockerfile", src=src, dst=doc, keep_path=False)
        copy(self, "docker-run.sh", src=src, dst=doc, keep_path=False)
        copy(self, "examples/*", src=src, dst=os.path.join(doc, "examples"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
