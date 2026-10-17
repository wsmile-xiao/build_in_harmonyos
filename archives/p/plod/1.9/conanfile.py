#!/usr/bin/env python3
"""Conan recipe for PLOD 1.9, a single-file Perl logging utility."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PlodConan(ConanFile):
    name = "plod"
    version = "1.9"
    description = "Personal LOgging Device command-line utility"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://web.archive.org/web/20160821040241/https://deer-run.com/~hal/plod/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # No upstream patches exist for plod (conandata patches: {}), so this is
        # a no-op; kept for G1 structural completeness of the recipe.
        apply_conandata_patches(self)

    def _perl(self):
        dependency = self.dependencies["perl"]
        executable = os.path.join(dependency.package_folder, "bin", "perl")
        if not os.path.isfile(executable):
            raise ConanException(f"Perl interpreter not found: {executable}")
        return executable

    def build(self):
        # Upstream ships no test suite and needs no compilation. A syntax check
        # is run only for native builds. Cross builds cannot execute the target
        # OHOS Perl binary. Run test_package directly on the HarmonyOS computer.
        script = os.path.join(self.source_folder, "plod")
        if can_run(self):
            self.run(f'"{self._perl()}" -c "{script}"')
        else:
            self.output.info("Host build: Perl checks remain pending until test_package runs on HarmonyOS")

    def package(self):
        source_script = os.path.join(self.source_folder, "plod")
        if not os.path.isfile(source_script):
            raise ConanException(f"PLOD script not found: {source_script}")

        with open(source_script, "r", encoding="latin-1") as handle:
            content = handle.read()

        old_shebang = "#!/usr/local/bin/perl"
        old_crypt = '$CRYPTCMD = "/usr/bin/crypt";'
        if not content.startswith(old_shebang):
            raise ConanException("Unexpected PLOD shebang; refusing a blind rewrite")
        if content.count(old_crypt) != 1:
            raise ConanException("Unexpected PLOD CRYPTCMD default; refusing a blind rewrite")

        # OHOS has no /usr/local/bin/perl or legacy /usr/bin/crypt. hicmd
        # installs runtime tools under /data/service/hnp/bin; encryption remains
        # opt-in through the existing CRYPTCMD environment/config override.
        content = content.replace(old_shebang, "#!/data/service/hnp/bin/perl", 1)
        content = content.replace(old_crypt, '$CRYPTCMD = "";', 1)

        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        packaged_script = os.path.join(bindir, "plod")
        with open(packaged_script, "w", encoding="latin-1", newline="") as handle:
            handle.write(content)
        os.chmod(packaged_script, 0o755)

        copy(self, "plod.1.gz", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "plod.el", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "emacs", "site-lisp"),
             keep_path=False)
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "plod"),
             keep_path=False)
        copy(self, "TODO", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "plod"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PATH", bindir)
        self.buildenv_info.prepend_path("PATH", bindir)
