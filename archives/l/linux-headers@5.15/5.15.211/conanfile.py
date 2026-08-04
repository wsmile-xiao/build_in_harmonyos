#!/usr/bin/env python3
"""Conan recipe for linux-headers@5.15 5.15.211."""
import hashlib
import os
import shutil
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, unzip
from conan.tools.layout import basic_layout


class LinuxHeadersConan(ConanFile):
    name = "linux-headers-5.15"
    version = "5.15.211"
    description = "Linux 5.15 UAPI headers"
    license = "GPL-2.0-only WITH Linux-syscall-note"
    homepage = "https://www.kernel.org/"
    url = ""
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        self.tool_requires("rsync/3.3.0")

    def generate(self):
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _source_filename(url):
        return os.path.basename(urlparse(url).path)

    def _candidate_source_urls(self):
        urls = self.conan_data["sources"]["url"]
        if isinstance(urls, str):
            return [urls]
        return list(urls)

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _download_cache_dir(self):
        cache = os.environ.get("DOWNLOAD_CACHE")
        if cache:
            try:
                os.makedirs(cache, exist_ok=True)
                return cache
            except OSError as exc:
                self.output.warning(f"DOWNLOAD_CACHE is not usable: {exc}")
        return self.source_folder

    def _cache_path_for(self, url):
        return os.path.join(self._download_cache_dir(), self._source_filename(url))

    def _cached_archive(self, sha256):
        for url in self._candidate_source_urls():
            path = self._cache_path_for(url)
            if os.path.isfile(path):
                actual = self._sha256(path)
                if actual == sha256:
                    self.output.info(f"Using cached source archive: {path}")
                    return path
                self.output.warning(
                    f"Ignoring cached archive with unexpected sha256: {path}"
                )
        return None

    @staticmethod
    def _env_int(name, default, minimum):
        raw_value = os.environ.get(name, str(default))
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ConanException(
                f"{name} must be an integer, got {raw_value!r}"
            ) from exc
        if value < minimum:
            raise ConanException(
                f"{name} must be at least {minimum}, got {raw_value!r}"
            )
        return value

    @classmethod
    def _download_settings(cls):
        return (
            cls._env_int("OHPCD_SOURCE_MAX_SECONDS", 1500, 1),
            cls._env_int("OHPCD_SOURCE_MIN_BYTES_PER_SECOND", 65536, 1),
            cls._env_int("OHPCD_SOURCE_MIN_RATE_GRACE", 120, 0),
            cls._env_int("OHPCD_SOURCE_READ_TIMEOUT", 30, 1),
        )

    def _download_archive(self, url, destination, sha256):
        max_seconds, min_rate, grace, read_timeout = self._download_settings()
        tmp = f"{destination}.part"
        digest = hashlib.sha256()
        downloaded = 0
        started = time.monotonic()
        last_report = started

        self.output.info(
            f"Downloading {url} with bounded source fallback "
            f"(max {max_seconds}s per URL)"
        )
        request = Request(url, headers={"User-Agent": "ohpcd-conan-source/1.0"})
        try:
            with urlopen(request, timeout=read_timeout) as response:
                with open(tmp, "wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)
                        now = time.monotonic()
                        elapsed = max(now - started, 0.001)
                        report_interval_reached = now - last_report >= 30
                        size_interval_reached = (
                            downloaded % (8 * 1024 * 1024) < len(chunk)
                        )
                        if report_interval_reached or size_interval_reached:
                            self.output.info(
                                f"Downloaded {downloaded // 1024}KB from "
                                f"{urlparse(url).netloc}"
                            )
                            last_report = now
                        if elapsed > max_seconds:
                            raise ConanException(
                                f"source download exceeded {max_seconds}s for {url}"
                            )
                        if elapsed > grace and downloaded / elapsed < min_rate:
                            raise ConanException(
                                "source download too slow for CI timeout "
                                f"({int(downloaded / elapsed)} B/s) from {url}"
                            )
            actual = digest.hexdigest()
            if actual != sha256:
                raise ConanException(
                    f"source archive sha256 mismatch for {url}: "
                    f"expected {sha256}, got {actual}"
                )
            os.replace(tmp, destination)
            return destination
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def _fetch_source_archive(self):
        sha256 = self.conan_data["sources"]["sha256"]
        cached = self._cached_archive(sha256)
        if cached:
            return cached

        errors = []
        for url in self._candidate_source_urls():
            destination = self._cache_path_for(url)
            try:
                return self._download_archive(url, destination, sha256)
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                self.output.warning(f"Source URL failed, trying next: {exc}")
        raise ConanException(
            "All source URLs failed:\n" + "\n".join(errors)
        )

    def source(self):
        archive = self._fetch_source_archive()
        unzip(self, archive, destination=self.source_folder, strip_root=True)

    def build(self):
        pass

    def _make_args(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = (
            compilers.get("c")
            or os.environ.get("CC")
            or shutil.which("clang")
            or shutil.which("cc")
            or "cc"
        )
        cxx = (
            compilers.get("cpp")
            or compilers.get("cxx")
            or os.environ.get("CXX")
            or shutil.which("clang++")
            or shutil.which("c++")
            or "c++"
        )
        host_cc = os.environ.get("HOSTCC") or shutil.which("cc") or cc
        host_cxx = os.environ.get("HOSTCXX") or shutil.which("c++") or cxx
        return f'HOSTCC="{host_cc}" HOSTCXX="{host_cxx}" CC="{cc}"'

    @staticmethod
    def _kernel_arch(conan_arch):
        if conan_arch.startswith("armv8"):
            return "arm64"
        if conan_arch == "x86_64":
            return "x86"
        return conan_arch

    @staticmethod
    def _path_prefix_command(bin_dir, command):
        escaped = bin_dir.replace('"', '\\"')
        return f'PATH="{escaped}:$PATH" {command}'

    def _dependency_package_folder(self, dependency_name):
        for dependency_group in (self.dependencies.build, self.dependencies.host):
            for _, dependency in dependency_group.items():
                ref = getattr(dependency, "ref", None)
                if getattr(ref, "name", None) == dependency_name:
                    return dependency.package_folder
        return None

    def _rsync_bin_dir(self):
        package_folder = self._dependency_package_folder("rsync")
        if not package_folder:
            raise ConanException("rsync/3.3.0 tool requirement was not resolved")
        bin_dir = os.path.join(package_folder, "bin")
        executable = os.path.join(bin_dir, "rsync")
        if not os.path.isfile(executable):
            raise ConanException(
                f"rsync/3.3.0 did not provide executable: {executable}"
            )
        return bin_dir

    def package(self):
        arch = self._kernel_arch(str(self.settings.arch))
        make_command = (
            f'make {self._make_args()} headers_install ARCH={arch} '
            f'INSTALL_HDR_PATH="{self.package_folder}"'
        )
        self.run(
            self._path_prefix_command(self._rsync_bin_dir(), make_command),
            cwd=self.source_folder,
            env="conanbuild",
        )
        license_src = os.path.join(self.source_folder, "COPYING")
        if os.path.exists(license_src):
            licenses = os.path.join(self.package_folder, "licenses")
            os.makedirs(licenses, exist_ok=True)
            copy(self, "COPYING", src=self.source_folder, dst=licenses, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = ["include"]
