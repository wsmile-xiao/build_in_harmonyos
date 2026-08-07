#!/usr/bin/env python3
"""Conan recipe for s6 2.15.1.0 — skarnet.org supervision suite.

s6 uses skarnet's own configure + make system (not standard autotools/cmake).
It depends on skalibs and execline, which are also skarnet.org packages.
Since skalibs/execline are not published to the conan registry, this recipe
builds all three from source in dependency order: skalibs → execline → s6.

Patch 0001-fifo-to-socket.patch replaces FIFO IPC with Linux abstract
namespace DGRAM socket for HarmonyOS HMDFS compatibility.
"""
import os
import shutil
import tarfile
import urllib.request
import time
import hashlib

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class S6Conan(ConanFile):
    name = "s6"
    version = "2.15.1.0"
    description = "skarnet.org s6 — small supervision suite (s6-svscan, s6-supervise, s6-svc, etc.)"
    license = "ISC"
    homepage = "https://skarnet.org/software/s6/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def _download_with_retry(self, url, dest, retries=3):
        for attempt in range(retries):
            try:
                urllib.request.urlretrieve(url, dest)
                return
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(2)

    def source(self):
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        archive_path = os.path.join(self.export_sources_folder, "s6.tar.gz")
        if not os.path.exists(archive_path):
            self.output.info(f"Downloading s6 source from {url}")
            self._download_with_retry(url, archive_path)
        h = hashlib.sha256()
        with open(archive_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        if h.hexdigest() != sha256:
            raise Exception(f"SHA256 mismatch: expected {sha256}")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=self.source_folder)
        extracted_dir = os.path.join(self.source_folder, f"s6-{self.version}")
        if os.path.isdir(extracted_dir):
            for item in os.listdir(extracted_dir):
                src = os.path.join(extracted_dir, item)
                dst = os.path.join(self.source_folder, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)
            os.rmdir(extracted_dir)

    def build(self):
        apply_conandata_patches(self)
        stage_dir = os.path.join(self.build_folder, "stage")
        os.makedirs(stage_dir, exist_ok=True)

        # Step 1: Build skalibs
        skalibs_url = "https://skarnet.org/software/skalibs/skalibs-2.15.1.0.tar.gz"
        skalibs_archive = os.path.join(self.build_folder, "skalibs.tar.gz")
        if not os.path.exists(skalibs_archive):
            self.output.info("Downloading skalibs source...")
            self._download_with_retry(skalibs_url, skalibs_archive)
        skalibs_src = os.path.join(self.build_folder, "skalibs-2.15.1.0")
        if not os.path.isdir(skalibs_src):
            with tarfile.open(skalibs_archive, "r:gz") as tar:
                tar.extractall(path=self.build_folder)
        self.output.info("Building skalibs...")
        self.run(f"cd {skalibs_src} && "
                 f"./configure --prefix={stage_dir} --disable-shared "
                 f"CPPFLAGS=-I{stage_dir}/include LDFLAGS=-L{stage_dir}/lib",
                 env="conanbuild")
        self.run(f"cd {skalibs_src} && make -j1", env="conanbuild")
        self.run(f"cd {skalibs_src} && make install", env="conanbuild")

        # Step 2: Build execline
        execline_url = "https://skarnet.org/software/execline/execline-2.9.9.2.tar.gz"
        execline_archive = os.path.join(self.build_folder, "execline.tar.gz")
        if not os.path.exists(execline_archive):
            self.output.info("Downloading execline source...")
            self._download_with_retry(execline_url, execline_archive)
        execline_src = os.path.join(self.build_folder, "execline-2.9.9.2")
        if not os.path.isdir(execline_src):
            with tarfile.open(execline_archive, "r:gz") as tar:
                tar.extractall(path=self.build_folder)
        self.output.info("Building execline...")
        self.run(f"cd {execline_src} && "
                 f"./configure --prefix={stage_dir} --disable-shared "
                 f"--with-skalibs={stage_dir} --with-lib={stage_dir}/lib "
                 f"CPPFLAGS=-I{stage_dir}/include LDFLAGS=-L{stage_dir}/lib",
                 env="conanbuild")
        self.run(f"cd {execline_src} && make -j1", env="conanbuild")
        self.run(f"cd {execline_src} && make install", env="conanbuild")

        # Step 3: Build s6
        self.output.info("Building s6...")
        s6_src = self.source_folder
        self.run(f"cd {s6_src} && "
                 f"./configure --prefix={stage_dir} --disable-shared "
                 f"--with-skalibs={stage_dir} --with-execline={stage_dir} "
                 f"--with-lib={stage_dir}/lib "
                 f"CPPFLAGS=-I{stage_dir}/include LDFLAGS=-L{stage_dir}/lib",
                 env="conanbuild")
        self.run(f"cd {s6_src} && make -j1", env="conanbuild")
        self.run(f"cd {s6_src} && make install", env="conanbuild")

    def package(self):
        bin_dir = os.path.join(self.build_folder, "stage", "bin")
        if os.path.isdir(bin_dir):
            copy(self, "*", bin_dir, os.path.join(self.package_folder, "bin"))
        lib_dir = os.path.join(self.build_folder, "stage", "lib")
        if os.path.isdir(lib_dir):
            copy(self, "*.a", lib_dir, os.path.join(self.package_folder, "lib"))
        inc_dir = os.path.join(self.build_folder, "stage", "include")
        if os.path.isdir(inc_dir):
            copy(self, "*", inc_dir, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
