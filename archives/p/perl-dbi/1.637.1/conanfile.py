#!/usr/bin/env python3
"""Conan recipe — perl-dbi 1.637 (auto-generated for Perl 5.42.2 rebuild)

R1:  Only --prefix (PERL_MM_OPT)
R26: No system same-name library (Perl XS module, not a system lib)
R27: No external Conan dependencies
R32: settings.os in ("Linux", "OHOS")
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PerlDbi(ConanFile):
    name = "perl-dbi"
    version = "1.637.1"
    description = "perl-dbi 1.637"
    license = "Artistic-1.0"
    homepage = "https://metacpan.org/pod/dbi"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported os: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_perl(self):
        """Find the perl executable. On CI workers, perl may not be in PATH."""
        perl = shutil.which("perl")
        if perl:
            return perl
        common_paths = [
            "/data/service/hnp/bin/perl",
            os.path.expanduser("~/usr/local/bin/perl"),
        ]
        for p in common_paths:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return "perl"

    def _get_perl_paths(self):
        """Get sitelib and archname from perl dynamically."""
        perl = self._find_perl()
        try:
            result = subprocess.run(
                [perl, "-V:sitelib"], capture_output=True, text=True, timeout=10
            )
            sitelib = result.stdout.strip()
            if "=" in sitelib:
                sitelib = sitelib.split("=", 1)[1].strip(";").strip("'")
        except Exception:
            sitelib = os.path.join(
                os.path.expanduser("~"), "usr", "local", "lib", "perl5", "site_perl", "5.42.2"
            )
        try:
            result = subprocess.run(
                [perl, "-V:archname"], capture_output=True, text=True, timeout=10
            )
            archname = result.stdout.strip()
            if "=" in archname:
                archname = archname.split("=", 1)[1].strip(";").strip("'")
        except Exception:
            archname = "aarch64-linux"
        return sitelib, archname

    def _run_cmd(self, cmd, cwd=None, check=True):
        """Run a command with proper Perl environment."""
        env = os.environ.copy()
        sitelib, archname = self._get_perl_paths()
        perl_arch_dir = os.path.join(sitelib, archname)
        existing = env.get("PERL5LIB", "")
        if existing:
            env["PERL5LIB"] = f"{sitelib}:{perl_arch_dir}:{existing}"
        else:
            env["PERL5LIB"] = f"{sitelib}:{perl_arch_dir}"
        self.output.info(f"Running: {cmd}")
        result = subprocess.run(
            cmd, shell=True, env=env, cwd=cwd,
            capture_output=True, text=True, timeout=300
        )
        if result.stdout:
            self.output.info(result.stdout)
        if result.stderr:
            self.output.warning(result.stderr)
        if check and result.returncode != 0:
            raise Exception(f"Command failed (exit {result.returncode}): {cmd}")
        return result

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        perl = self._find_perl()
        self._run_cmd(f"{perl} Makefile.PL", cwd=src)
        if self.settings.os == "OHOS":
            makefile = os.path.join(src, "Makefile")
            if os.path.exists(makefile):
                with open(makefile, "r") as mf:
                    content = mf.read()
                if "-nostartfiles" not in content:
                    content = content.replace(
                        "LDDLFLAGS =",
                        "LDDLFLAGS = -nostartfiles -nodefaultlibs -L/system/lib64 -lc"
                    )
                with open(makefile, "w") as mf:
                    mf.write(content)
        self._run_cmd("make -j1", cwd=src)

    def package(self):
        dest = self.package_folder
        src = self.source_folder
        self._run_cmd(f'make install DESTDIR="{dest}"', cwd=src)
        for root, dirs, files in os.walk(dest):
            for fn in files:
                if fn.endswith(".so"):
                    lib_dir = os.path.join(dest, "lib")
                    os.makedirs(lib_dir, exist_ok=True)
                    shutil.copy2(os.path.join(root, fn), lib_dir)

    def package_info(self):
        self.cpp_info.libs = ["DBI"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
