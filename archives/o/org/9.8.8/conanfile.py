#!/usr/bin/env python3
"""Conan recipe for GNU ELPA org 9.8.8."""

import os
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout


class OrgConan(ConanFile):
    name = "org"
    version = "9.8.8"
    description = "Outline-based notes management and organizer for GNU Emacs"
    license = "GPL-3.0-or-later"
    homepage = "https://orgmode.org"
    url = "https://orgmode.org"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def requirements(self):
        self.requires("emacs/29.1")

    def source(self):
        source = self.conan_data["sources"]
        archive = os.path.join(self.source_folder, f"org-{self.version}.tar.lz")
        download(self, source["url"], archive, sha256=source["sha256"])

        tar = self._find_tar()
        try:
            self._extract_tar(tar, archive)
        except subprocess.CalledProcessError:
            self.output.info("system tar could not unpack .tar.lz directly; using lzip fallback")
            lzip = self._find_or_build_lzip()
            tar_path = archive[:-3]
            subprocess.run([lzip, "-d", "-k", "-f", archive], check=True)
            self._extract_tar(tar, tar_path)
            os.unlink(tar_path)
        os.unlink(archive)

    def _find_tar(self):
        tar = shutil.which("tar")
        if not tar:
            raise ConanException("system tar is required to unpack GNU ELPA .tar.lz sources")
        return tar

    def _extract_tar(self, tar, archive):
        subprocess.run(
            [tar, "-xf", archive, "--strip-components=1", "-C", self.source_folder],
            check=True,
        )

    def _find_or_build_lzip(self):
        lzip = shutil.which("lzip")
        if lzip:
            return lzip

        lzip_url = "https://download-mirror.savannah.gnu.org/releases/lzip/lzip-1.25.tar.gz"
        lzip_sha256 = "09418a6d8fb83f5113f5bd856e09703df5d37bae0308c668d0f346e3d3f0a56f"
        lzip_archive = os.path.join(self.source_folder, "lzip-1.25.tar.gz")
        lzip_prefix = os.path.join(self.source_folder, ".lzip")
        download(self, lzip_url, lzip_archive, sha256=lzip_sha256)
        with tarfile.open(lzip_archive, "r:gz") as tf:
            tf.extractall(self.source_folder, filter="data")
        os.unlink(lzip_archive)

        lzip_src = os.path.join(self.source_folder, "lzip-1.25")
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        cc = os.environ.get("CC") or compilers.get("c") or "clang"
        cxx = os.environ.get("CXX") or compilers.get("cpp") or "clang++"
        tmp_dir = os.path.join(self.source_folder, ".tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        env = os.environ.copy()
        env.setdefault("TMPDIR", tmp_dir)
        env.setdefault("TMP", tmp_dir)
        env.setdefault("TEMP", tmp_dir)
        subprocess.run(
            ["./configure", f"--prefix={lzip_prefix}", f"CC={cc}", f"CXX={cxx}"],
            cwd=lzip_src,
            check=True,
            env=env,
        )
        subprocess.run(["make", "-j1"], cwd=lzip_src, check=True, env=env)
        subprocess.run(["make", "install"], cwd=lzip_src, check=True, env=env)
        shutil.rmtree(lzip_src, ignore_errors=True)
        return os.path.join(lzip_prefix, "bin", "lzip")

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        # The GNU ELPA tarball ships generated org-loaddefs.el and
        # org-version.el, but no upstream test suite. Load the package with the
        # packaged source directory first in load-path to catch missing files.
        emacs = shlex.quote(os.environ.get("EMACS", "emacs"))
        source = shlex.quote(self.source_folder)
        expr = (
            "(progn "
            "(require 'org) "
            "(require 'ol) "
            "(unless (string= (org-version) \"9.8.8\") "
            "(error \"unexpected org-version: %S\" (org-version))) "
            "(unless (fboundp 'org-link-set-parameters) "
            "(error \"org-link-set-parameters missing\")))"
        )
        self.run(
            f"{emacs} -Q --batch -L {source} --eval {shlex.quote(expr)}",
            env="conanrun",
        )

    def package(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"org-{self.version}",
        )
        copy(self, "*.el", self.source_folder, lisp_dir, keep_path=False)

        share_dir = os.path.join(self.package_folder, "share", "org")
        for pattern in ("README*", "CONTRIBUTE.org", "*.info"):
            copy(self, pattern, self.source_folder, share_dir, keep_path=False)
        copy(
            self,
            "*",
            os.path.join(self.source_folder, "etc"),
            os.path.join(share_dir, "etc"),
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        lisp_dir = os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"org-{self.version}",
        )

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

        self.buildenv_info.define_path("ORG_LISPDIR", lisp_dir)
        self.runenv_info.define_path("ORG_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
