#!/usr/bin/env python3
"""Conan test_package — openbabel/3.1.1 consumer end-to-end test (L1).

Builds and runs a real consumer of the packaged library on the OHOS
device: SMILES parse -> canonical SMILES/formula -> MOL round-trip ->
InChI generation -> MW descriptor (see test_openbabel.cpp).

The test binary is a freshly produced ELF on a user volume, so on OHOS
it is signed with binary-sign-tool before execution (HMDFS transiently
rejects execve on fresh ELFs — retried).  Runtime data files (atom
typing, aromaticity rules ...) are resolved through BABEL_DATADIR
pointing at the packaged share/openbabel data directory; shared deps
(libxml2.so.16) resolve through the conanrun environment.
"""
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class OpenbabelTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign(self, path):
        signer = None
        for cand in (os.environ.get("OHOS_BINARY_SIGN_TOOL"),
                     "/data/service/hnp/bin/binary-sign-tool",
                     "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"):
            if cand and os.path.isfile(cand):
                signer = cand
                break
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; %s may be rejected by OHOS" % path)
            return
        directory = os.path.dirname(path)
        tmp_in = os.path.join(directory, ".%s.sign-%d" % (
            os.path.basename(path), os.getpid()))
        tmp_out = tmp_in + ".signed"
        try:
            shutil.copy2(path, tmp_in)
            result = subprocess.run(
                [signer, "sign", "-selfSign", "1", "-inFile", tmp_in,
                 "-outFile", tmp_out, "-signAlg", "SHA256withECDSA"],
                capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.isfile(tmp_out):
                shutil.move(tmp_out, path)
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
        finally:
            for leftover in (tmp_in, tmp_out):
                if os.path.isfile(leftover):
                    try:
                        os.remove(leftover)
                    except OSError:
                        pass

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_openbabel")
        if str(self.settings.os) == "OHOS" and os.path.isfile(binary):
            self._sign(binary)
        # BABEL_DATADIR must reach the process environment; shared deps
        # (libxml2.so.16) resolve through the conanrun environment files.
        dep = self.dependencies["openbabel"]
        datadir = os.path.join(dep.package_folder, "share", "openbabel")
        if os.path.isdir(datadir):
            os.environ["BABEL_DATADIR"] = datadir
        # HMDFS: a freshly written (signed) ELF can transiently fail execve
        # with EACCES for minutes; retry a few times before giving up.
        last_exc = None
        for attempt in range(5):
            try:
                self.run('"%s"' % binary, env=["conanrun"])
                return
            except (PermissionError, ConanException) as exc:
                last_exc = exc
                time.sleep(15)
        raise ConanException(
            "test_openbabel could not be executed: %s" % last_exc)
