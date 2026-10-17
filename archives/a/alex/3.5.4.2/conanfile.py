#!/usr/bin/env python3
"""Conan 2.x recipe — alex 3.5.4.2 (Haskell lexer generator)

Alex is a tool for generating lexical analysers in Haskell (BSD-3-Clause).
It is itself a Haskell program: built with GHC via the cabal
`build-type: Simple` Setup.hs flow. There is no GHC in the base OHOS
toolchain, so the recipe provisions it through the harmonybrew formula
(`brew install ghc`), mirroring how the aiken recipe provisions rust.
Host == target (OHOS aarch64 native), so `runghc Setup.hs configure/build`
runs natively; only GHC boot libraries (array/base/containers/mtl/...) are
needed, no external Haskell packages.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AlexConan(ConanFile):
    name = "alex"
    version = "3.5.4.2"
    description = "Alex is a tool for generating lexical analysers in Haskell"
    license = "BSD-3-Clause"
    homepage = "https://haskell-alex.readthedocs.io"
    url = "https://github.com/haskell/alex"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"alex supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Set writable TMPDIR on OHOS (/tmp is read-only)
        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/alex")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        # Ensure Haskell toolchain (GHC) is available via harmonybrew
        self._ensure_haskell_toolchain()

        # cabal build-type: Simple — configure then build via Setup.hs.
        # configure --prefix=/usr so `copy --destdir=` lands a clean
        # <pkg>/usr/bin/alex layout (normalized in package()).
        # --enable-executable-static: GHC links libgmp/libffi statically so
        # the binary has no runtime shared-library deps (libgmp.so.10 /
        # libffi.so.8 are absent from the OHOS system loader path).
        self.run(
            f"cd {self.source_folder} && runghc Setup.hs configure "
            "--prefix=/usr --enable-executable-static",
            env="conanbuild",
        )
        self.run(f"cd {self.source_folder} && runghc Setup.hs build", env="conanbuild")

    def package(self):
        # Copy the UNSTRIPPED built binary straight from the GHC dist dir.
        # `runghc Setup.hs copy` strips the executable, and stripped GHC ELFs
        # cannot exec on OHOS (EPERM / Permission denied); the unstripped
        # dist binary runs fine (verified: --version/--help/.x all pass).
        import glob

        found = glob.glob(
            os.path.join(self.build_folder, "**", "dist", "build", "alex", "alex"),
            recursive=True,
        )
        if not found:
            found = glob.glob(
                os.path.join(self.source_folder, "**", "dist", "build", "alex", "alex"),
                recursive=True,
            )
        assert found, "alex binary not found under build/source folders"
        copy(self, "alex", os.path.dirname(found[0]),
             os.path.join(self.package_folder, "bin"))
        # alex needs its runtime templates (AlexTemplate.hs/AlexWrappers.hs);
        # by default it looks at a build-time baked absolute datadir, so ship
        # them relocatably under share/ and let consumers pass --template=DIR
        # (the alex CLI override; the test_package does exactly this).
        share_dir = os.path.join(self.package_folder, "share", "alex-3.5.4.2")
        os.makedirs(share_dir, exist_ok=True)
        data_dir = os.path.join(self.source_folder, "data")
        for tpl in ("AlexTemplate.hs", "AlexWrappers.hs"):
            if os.path.isfile(os.path.join(data_dir, tpl)):
                copy(self, tpl, data_dir, share_dir)
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []

    def _ensure_haskell_toolchain(self):
        """Install GHC via harmonybrew if runghc/ghc is not available."""
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        if shutil.which("runghc") or shutil.which("ghc"):
            return
        if os.path.isfile(os.path.join(brew_bin, "ghc")):
            os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
            return
        # Install harmonybrew if not present (CI workers may lack it).
        if not os.path.isfile(os.path.expanduser("~/.harmonybrew/bin/brew")):
            # CI workers' curl may lack CA certs (known issue, cf. siril/imgp):
            # point curl at an existing CA bundle so the harmonybrew install
            # and the ghc bottle fetch can verify the server.
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
        os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
