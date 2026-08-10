#!/usr/bin/env python3
"""Conan recipe for apcupsd 3.14.14 — APC UPS power management daemon.

apcupsd is a command-line application for monitoring UPSes and performing
graceful shutdown during power failure.

Platform adaptations for HarmonyOS (OHOS):
  - Replace config.guess/config.sub for platform detection
  - Fix HMDFS temporary file creation in configure
  - Guard pthread_cancel via feature detection (HAVE_PTHREAD_CANCEL, R8 compliant)
  - Provide wrapper scripts for missing tools (wall, mail, man, col)
  - Override SHUTDOWN to use poweroff instead of shutdown
  - Fix sbindir/sysconfdir (configure hardcodes /sbin, /etc/apcupsd)
  - Set STRIP= during install (install cmd misinterprets strip program name)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ApcupsdConan(ConanFile):
    name = "apcupsd"
    version = "3.14.14"
    description = "APC UPS power management daemon"
    license = "GPL-2.0-only"
    homepage = "https://apcupsd.org/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _create_wrappers(self):
        """Create wrapper scripts for tools missing on HarmonyOS."""
        bin_dir = os.path.join(self.source_folder, "_wrappers", "bin")
        os.makedirs(bin_dir, exist_ok=True)

        wrappers = {
            "wall": '#!/bin/sh\necho "$1"\n',
            "mail": "#!/bin/sh\n",
            "man": '#!/bin/sh\ncat "$2" 2>/dev/null\n',
            "col": "#!/bin/sh\ncat\n",
        }

        for name, content in wrappers.items():
            path = os.path.join(bin_dir, name)
            with open(path, "w") as f:
                f.write(content)
            os.chmod(path, 0o755)

        return bin_dir

    def _fix_variables_mak(self):
        """Fix sbindir/sysconfdir/HALPOLICYDIR in generated variables.mak.

        Configure regenerates variables.mak from variables.mak.in,
        overriding any pre-applied patches. We fix the generated file directly.
        """
        vmak = os.path.join(self.source_folder, "autoconf", "variables.mak")
        if not os.path.isfile(vmak):
            return

        with open(vmak, "r") as f:
            content = f.read()

        content = content.replace("sbindir = /sbin", "sbindir = ${exec_prefix}/sbin")
        content = content.replace(
            "sysconfdir = /etc/apcupsd", "sysconfdir = ${prefix}/etc/apcupsd"
        )
        content = content.replace(
            "HALPOLICYDIR = /usr/share/hal/fdi/policy/20thirdparty",
            "HALPOLICYDIR = ${datadir}/hal/fdi/policy/20thirdparty",
        )

        with open(vmak, "w") as f:
            f.write(content)

    def _detect_pthread_cancel(self):
        """Detect if pthread_cancel is available and define HAVE_PTHREAD_CANCEL.

        Proper feature detection (R8 compliant): checks by compiling a test
        program rather than relying on platform macros like __OHOS__.
        Uses $CC from the Conan build environment (R33 compliant).
        """
        test_dir = os.path.join(self.source_folder, ".tmp")
        os.makedirs(test_dir, exist_ok=True)
        test_src = os.path.join(test_dir, "_test_pcancel.c")
        test_bin = os.path.join(test_dir, "_test_pcancel.out")

        with open(test_src, "w") as f:
            f.write("#include <pthread.h>\n"
                    "int main(){pthread_cancel((pthread_t)0);return 0;}\n")

        try:
            self.run(f'$CC {test_src} -lpthread -o {test_bin} 2>/dev/null')
            # pthread_cancel is available - define the macro
            apcconfig = os.path.join(self.source_folder, "include", "apcconfig.h")
            with open(apcconfig, "a") as f:
                f.write("\n/* Detected by feature detection in conanfile.py */\n")
                f.write("#define HAVE_PTHREAD_CANCEL 1\n")
        except Exception:
            pass  # pthread_cancel not available, macro stays undefined
        finally:
            for path in (test_src, test_bin):
                if os.path.exists(path):
                    os.unlink(path)

    def build(self):
        apply_conandata_patches(self)

        # Create .tmp directory for HMDFS workaround
        os.makedirs(os.path.join(self.source_folder, ".tmp"), exist_ok=True)

        # Create wrapper scripts for missing tools
        bin_dir = self._create_wrappers()

        # Set environment variables directly (conan 2.x self.run env expects list)
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        os.environ["SHUTDOWN"] = "/bin/poweroff"
        os.environ["STRIP"] = ""

        # Configure (in-source build - apcupsd's configure expects it)
        prefix = self.package_folder
        self.run(
            f'./configure --prefix="{prefix}" '
            f'--sbindir="${{exec_prefix}}/sbin" '
            f'--sysconfdir="${{prefix}}/etc/apcupsd"'
        )

        # Fix variables.mak after configure (configure regenerates it)
        self._fix_variables_mak()

        # Feature detection: check if pthread_cancel is available (R8 compliant)
        # This is proper feature detection, not platform detection.
        # On HarmonyOS/musl, pthread_cancel is not available, so HAVE_PTHREAD_CANCEL
        # will not be defined, and the #ifdef guard in apcexec.c will skip the call.
        self._detect_pthread_cancel()

        # Build
        self.run("make -j1")

    def package(self):
        # STRIP= to prevent install from misinterpreting strip program name
        os.environ["STRIP"] = ""
        self.run("make install")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["sbin"]
