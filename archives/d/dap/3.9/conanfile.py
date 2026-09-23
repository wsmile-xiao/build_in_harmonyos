#!/usr/bin/env python3
"""Conan recipe — dap 3.9 (Autotools application, zero external deps)

GNU dap is a statistics/graphics tool producing four executables
(dap, dapruns, daprun, dappp). The GNU release tarball ships a
pre-generated configure; build-time fixes are the standard OHOS set:
E007 config.guess/sub replacement (build-aux), E490 exec-bit restore,
and the HMDFS getcwd/umask adaptation (adms/2.3.7 precedent).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DapConan(ConanFile):
    name = "dap"
    version = "3.9"
    description = "GNU dap 3.9 — statistics and graphics tool"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/dap/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)

        # E490: restore exec bits HMDFS adaptation paths may have dropped.
        for _script in ("configure", "config.guess", "config.sub", "install-sh",
                        "missing", "compile", "depcomp", "ltmain.sh"):
            for _sub in ("build-aux", ""):
                _path = os.path.join(self.source_folder, _sub, _script)
                if os.path.exists(_path):
                    os.chmod(_path, 0o755)

        # E007: the shipped build-aux config.guess/config.sub predate
        # HarmonyOS; replace with self-contained OHOS-aware versions.
        self._replace_config_for_ohos()

        # HMDFS getcwd fix (adms/2.3.7): preset PWD and give configure's
        # ac_pwd probe a $PWD fallback; tmp dirs umask 077 -> 022 (E011).
        os.environ["PWD"] = self.build_folder
        _configure = os.path.join(self.source_folder, "configure")
        with open(_configure) as f:
            _cfg = f.read()
        _cfg = _cfg.replace(
            "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&",
            "ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\ntest -n \"$ac_pwd\" &&",
        )
        _cfg = _cfg.replace("umask 077", "umask 022")
        with open(_configure, "w") as f:
            f.write(_cfg)

        autotools.configure()
        autotools.make(args=["-j1"])

    def _replace_config_for_ohos(self):
        """Replace build-aux config.guess/config.sub with OHOS-aware versions (E007)."""
        for _sub in ("build-aux", ""):
            _guess = os.path.join(self.source_folder, _sub, "config.guess")
            _sub_path = os.path.join(self.source_folder, _sub, "config.sub")
            if not os.path.isfile(_guess) and not os.path.isfile(_sub_path):
                continue

            ohos_config_guess = (
                '#!/bin/sh\n'
                '# OHOS-aware config.guess (self-contained)\n'
                'machine=$(uname -m 2>/dev/null || echo unknown)\n'
                'system=$(uname -s 2>/dev/null || echo unknown)\n'
                'case "$system" in\n'
                '    HarmonyOS|OHOS)\n'
                '        echo "${machine}-unknown-linux-ohos"\n'
                '        ;;\n'
                '    *)\n'
                '        echo "${machine}-unknown-linux-gnu"\n'
                '        ;;\n'
                'esac\n'
                'exit 0\n'
            )
            with open(_guess, "w") as f:
                f.write(ohos_config_guess)
            os.chmod(_guess, 0o755)

            ohos_config_sub = (
                '#!/bin/sh\n'
                '# OHOS-aware config.sub (self-contained)\n'
                '# Always pass through the input triplet\n'
                'if [ $# -eq 0 ] || [ -z "$1" ]; then\n'
                '    echo "aarch64-unknown-linux-ohos"\n'
                '    exit 0\n'
                'fi\n'
                'echo "$1"\n'
                'exit 0\n'
            )
            with open(_sub_path, "w") as f:
                f.write(ohos_config_sub)
            os.chmod(_sub_path, 0o755)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
