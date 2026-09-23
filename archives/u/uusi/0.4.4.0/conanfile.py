#!/usr/bin/env python3
"""Conan 2.x recipe - uusi 0.4.4.0.

uusi is a Haskell/Cabal tool for semantic .cabal-file rewrites.  The source
tarball ships a simple Setup.hs flow, so the recipe keeps to the same native
path as other Haskell tools in this repository:

- provision GHC through harmonybrew when it is not already present;
- compile `Setup.hs` with GHC and run the resulting Setup executable;
- use `--enable-executable-static` so the packaged executables do not depend
  on shared Haskell runtime libraries at execution time;
- run the upstream `uusi-tests` suite with a package-local HUnit-compatible
  module because external Haskell package adaptation belongs in a separate PR.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UusiConan(ConanFile):
    name = "uusi"
    version = "0.4.4.0"
    description = "A simple command-line program to tweak Cabal package descriptions"
    license = "MIT"
    homepage = "https://github.com/berberman/uusi"
    url = "https://hackage.haskell.org/package/uusi"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"uusi supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/uusi")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        self._ensure_haskell_toolchain()
        self._prepare_haskell_runtime_env()

        # build-type: Simple, so compiling Setup.hs with GHC avoids cabal-install
        # and stays portable across the Windows validation host and OHOS.
        ghc = self._ghc_executable()
        ghc_pkg = self._ghc_pkg_executable()
        setup_cmd = "Setup.exe" if os.name == "nt" else "./Setup"
        self.run(
            f'cd {self.source_folder} && "{ghc}" --make Setup.hs -o Setup',
            env="conanbuild",
        )
        self.run(
            f"cd {self.source_folder} && {setup_cmd} configure "
            f'--with-compiler="{ghc}" --with-hc-pkg="{ghc_pkg}" '
            "--prefix=/usr --enable-executable-static --enable-tests",
            env="conanbuild",
        )
        self.run(f"cd {self.source_folder} && {setup_cmd} build", env="conanbuild")
        self.run(
            f"cd {self.source_folder} && {setup_cmd} test --show-details=direct",
            env="conanbuild",
        )

    def package(self):
        for exe in ("uusi", "gen-setup", "uusi-extract"):
            found = glob.glob(
                os.path.join(self.build_folder, "**", "dist", "build", exe, exe),
                recursive=True,
            )
            if not found:
                found = glob.glob(
                    os.path.join(self.source_folder, "**", "dist", "build", exe, exe),
                    recursive=True,
                )
            if not found:
                raise ConanInvalidConfiguration(f"{exe} binary not found under dist/build")
            copy(self, exe, os.path.dirname(found[0]), os.path.join(self.package_folder, "bin"))

        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []

    def _ensure_haskell_toolchain(self):
        """Install GHC via harmonybrew if GHC is not already available."""
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        if self._ghc_executable():
            return
        if os.path.isfile(os.path.join(brew_bin, "ghc")):
            os.environ["PATH"] = brew_bin + os.pathsep + os.environ.get("PATH", "")
            return
        if not os.path.isfile(os.path.expanduser("~/.harmonybrew/bin/brew")):
            for cacert in (
                "/etc/ssl/certs/cacert.pem",
                os.path.expanduser("~/usr/local/ssl/cert.pem"),
            ):
                if os.path.isfile(cacert):
                    os.environ.setdefault("SSL_CERT_FILE", cacert)
                    os.environ.setdefault("CURL_CA_BUNDLE", cacert)
                    break
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild",
            )
        brew_path = os.path.expanduser("~/.harmonybrew/bin/brew")
        self.run(f"{brew_path} install ghc", env="conanbuild")
        os.environ["PATH"] = brew_bin + os.pathsep + os.environ.get("PATH", "")

    def _prepare_haskell_runtime_env(self):
        """Expose harmonybrew GHC runtime libraries to Setup and GHC subprocesses."""
        brew_prefix = os.path.expanduser("~/.harmonybrew")
        path_dirs = [os.path.join(brew_prefix, "bin")]
        if str(self.settings.os) == "OHOS":
            path_dirs.append("/data/service/hnp/bin")
        self._prepend_env_path("PATH", path_dirs)

        lib_dirs = [os.path.join(brew_prefix, "lib")]
        for pattern in (
            "~/.harmonybrew/Cellar/gmp/*/lib",
            "~/.harmonybrew/Cellar/libffi/*/lib",
            "~/.harmonybrew/Cellar/ncurses/*/lib",
            "~/.harmonybrew/Cellar/ghc/*/lib",
            "~/.harmonybrew/Cellar/ghc/*/lib/*-ghc-*",
        ):
            lib_dirs.extend(glob.glob(os.path.expanduser(pattern)))

        self._prepend_env_path("LD_LIBRARY_PATH", lib_dirs)
        self._prepend_env_path("LIBRARY_PATH", lib_dirs)

    @staticmethod
    def _prepend_env_path(name, paths):
        merged = []
        for path in paths:
            if path and os.path.isdir(path) and path not in merged:
                merged.append(path)
        for path in os.environ.get(name, "").split(os.pathsep):
            if path and path not in merged:
                merged.append(path)
        if merged:
            os.environ[name] = os.pathsep.join(merged)

    def _ghc_executable(self):
        """Return the first available GHC executable path."""
        for name in ("ghc", "ghc-9.14.1"):
            path = shutil.which(name)
            if path:
                return path
        return None

    def _ghc_pkg_executable(self):
        """Return the matching ghc-pkg executable path."""
        for name in ("ghc-pkg", "ghc-pkg-9.14.1"):
            path = shutil.which(name)
            if path:
                return path
        return self._ghc_executable()
