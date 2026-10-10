#!/usr/bin/env python3
"""Conan recipe — japi-compliance-checker 2.4 (JAPICC).

japi-compliance-checker (Java API Compliance Checker) is a pure Perl
tool that checks backward binary and source-level compatibility of a
Java library API: it extracts classes from jars/jmods, decompiles them
with `javap`, and compares the public API surface (methods, fields,
inheritance, annotations, ...).

The packaging follows the merged recipe of the sibling lvc tool
abi-compliance-checker/2.3 (identical upstream layout: <tool>.pl +
modules/ + a 2-line Makefile wrapper around Makefile.pl):

  * The upstream Makefile.pl installer has Perl 5.42+ compatibility
    issues (File::Spec import / Getopt::Long single-dash options), so
    the equivalent install steps run directly in build().
  * share/japi-compliance-checker/japi-compliance-checker.pl is the
    real entry point (MODULES_INSTALL_PATH replaced by the relative
    ../share/japi-compliance-checker path); bin/japi-compliance-checker
    is a wrapper that resolves its own location and calls the real
    script with a full $0, so getModules() finds the modules directory.

Runtime requirements: Perl 5 (core modules only: Getopt::Long,
File::*, Cwd, Data::Dumper, IPC::Open3, Digest::MD5, POSIX) and a JDK
(javap / jar / javac / java). build() resolves a JDK via JAVA_HOME,
~/bishengjdk17 (cmd-pkgs layout) or PATH — auto-installing BiSheng JDK
17.0.13 through the OpenHarmonyPCDeveloper cmd-pkgs installer when
none is found (same policy as archives/j/jackson-core 2.14.1) — and
then runs the upstream regression suite `japi-compliance-checker
-test` inside build() (R51): the suite generates a two-version sample
library, compiles and runs 30 test programs against it and requires
the checker to detect >= 100 API breaks (measured: 164, SUCCESS).

R32: validate() checks settings.os in ("Linux", "OHOS")
R34: test_package/ exercises the installed CLI on real jars
R38: CLI package -> software-level commands.json declares the binary
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
    load, save,
)
from conan.tools.layout import basic_layout


class JapiComplianceCheckerConan(ConanFile):
    name = "japi-compliance-checker"
    version = "2.4"
    description = (
        "Java API Compliance Checker (JAPICC) - check backward binary "
        "and source-level compatibility of a Java library API"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/lvc/japi-compliance-checker"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # L0p: OHOS profile requires all four settings (script tool: compiler
    # and build_type only feed the package_id, no compilation happens)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # JDK resolution (policy of archives/j/jackson-core 2.14.1 and
    # archives/j/jtreg8 8.3-1)
    def _ensure_java(self):
        java_home = os.environ.get("JAVA_HOME", "")
        if java_home and os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("Java found via JAVA_HOME=" + java_home)
            return java_home
        for candidate in [
            os.path.expanduser("~/bishengjdk17"),
            os.path.expanduser("~/usr/local/bishengjdk17"),
        ]:
            if os.path.isfile(os.path.join(candidate, "bin", "java")):
                self.output.info("Java found at " + candidate)
                return candidate
        java_in_path = shutil.which("java")
        if java_in_path:
            candidate = os.path.dirname(
                os.path.dirname(os.path.realpath(java_in_path)))
            self.output.info("Java found in PATH at " + candidate)
            return candidate
        self.output.info(
            "Java not found - installing bishengjdk 17.0.13 via cmd-pkgs...")
        install_url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
                       "/releases/download/pkgs/install-jdk.sh")
        script_path = os.path.join(os.path.expanduser("~"), ".install-jdk.sh")
        self.run('curl -fsSL -o "{}" "{}"'.format(script_path, install_url))
        self.run('sh "{}" 17.0.13'.format(script_path))
        java_home = os.path.expanduser("~/bishengjdk17")
        if os.path.isfile(os.path.join(java_home, "bin", "java")):
            self.output.info("bishengjdk 17.0.13 installed at " + java_home)
            return java_home
        raise ConanInvalidConfiguration(
            "Failed to find or install bishengjdk 17.0.13. Set JAVA_HOME "
            "or install via: curl -fsSL https://gitcode.com/"
            "OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/"
            "install-jdk.sh | sh -s -- 17.0.13")

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        tool_sname = "japi-compliance-checker"
        script_file = os.path.join(src, f"{tool_sname}.pl")

        # Read script content and replace the MODULES_INSTALL_PATH
        # placeholder with the install-relative modules path (same as
        # upstream Makefile.pl with DESTDIR, same as abi-compliance-checker).
        content = load(self, script_file)
        content = content.replace("MODULES_INSTALL_PATH",
                                  os.path.join("..", "share", tool_sname))

        # Install layout:
        #   share/japi-compliance-checker/japi-compliance-checker.pl (real)
        #   share/japi-compliance-checker/modules/                  (modules)
        #   bin/japi-compliance-checker                             (wrapper)
        install_dir = os.path.join(self.build_folder, "install")
        share_tool_dir = os.path.join(install_dir, "share", tool_sname)
        os.makedirs(share_tool_dir, exist_ok=True)

        real_script = os.path.join(share_tool_dir, f"{tool_sname}.pl")
        save(self, real_script, content)
        os.chmod(real_script, 0o755)

        modules_src = os.path.join(src, "modules")
        modules_dst = os.path.join(share_tool_dir, "modules")
        if os.path.isdir(modules_src):
            shutil.copytree(modules_src, modules_dst, dirs_exist_ok=True)

        bin_dir = os.path.join(install_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, tool_sname)
        wrapper_content = (
            "#!/usr/bin/env bash\n"
            'script_dir="$(cd "$(dirname "$0")" && pwd)"\n'
            f'exec perl "$script_dir/../share/{tool_sname}/{tool_sname}.pl" "$@"\n'
        )
        save(self, wrapper, wrapper_content)
        os.chmod(wrapper, 0o755)

        # ---- upstream regression suite (R51) -----------------------------
        java_home = self._ensure_java()
        run_dir = os.path.join(self.build_folder, "upstream-test")
        os.makedirs(run_dir, exist_ok=True)
        env = os.environ.copy()
        env["PATH"] = (os.path.join(java_home, "bin") + ":" +
                       bin_dir + ":" + env.get("PATH", ""))
        self.output.info("Running upstream test suite: "
                         "japi-compliance-checker -test")
        try:
            proc = subprocess.run(
                [tool_sname, "-test"], cwd=run_dir, env=env,
                capture_output=True, text=True, timeout=1800)
        except subprocess.TimeoutExpired:
            raise ConanException(
                "upstream -test suite timed out after 1800s")
        output = (proc.stdout or "") + (proc.stderr or "")
        self.output.info("upstream -test tail:\n" + output[-1500:])
        if proc.returncode != 0 or "Test result: SUCCESS" not in output:
            raise ConanException(
                "upstream -test suite failed (rc={}): {}".format(
                    proc.returncode, output[-500:]))

    def package(self):
        install_dir = os.path.join(self.build_folder, "install")

        copy(self, "*", src=os.path.join(install_dir, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*", src=os.path.join(install_dir, "share"),
             dst=os.path.join(self.package_folder, "share"), keep_path=True)

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
