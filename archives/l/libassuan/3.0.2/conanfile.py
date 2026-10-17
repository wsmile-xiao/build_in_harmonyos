#!/usr/bin/env python3
"""Conan recipe for libassuan 3.0.2 on OpenHarmony."""

import hashlib
import os
import shlex
import shutil
from contextlib import contextmanager

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    patch,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.gnu.autotools import load_toolchain_args
from conan.tools.layout import basic_layout


class LibassuanConan(ConanFile):
    name = "libassuan"
    version = "3.0.2"
    description = "IPC library implementing the Assuan protocol"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnupg.org/software/libassuan/"
    url = "https://git.gnupg.org/cgi-bin/gitweb.cgi?p=libassuan.git"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires(
            "libgpg-error/1.55",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libassuan/3.0.2 supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--prefix=/",
                "--libdir=/lib",
                "--includedir=/include",
                "--build=aarch64-unknown-linux-musl",
                "--host=aarch64-unknown-linux-musl",
                "--disable-doc",
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--disable-static" if self.options.shared else "--enable-static",
                "--with-libgpg-error-prefix={}".format(
                    self.dependencies["libgpg-error"].package_folder
                ),
            ]
        )
        tc.generate()

    def build(self):
        native_root = self._native_root()
        self._remove_native_root(native_root, "before build")
        native_source = os.path.join(native_root, "source")
        native_build = os.path.join(native_root, "build")
        native_stage = os.path.join(native_root, "stage")
        shutil.copytree(self.source_folder, native_source, symlinks=True)
        os.makedirs(native_build)
        self._apply_patches(native_source)
        configure_args = load_toolchain_args(self.generators_folder)["configure_args"]
        self.output.info("native root: {}".format(native_root))
        try:
            with self._build_environment(native_root):
                self._run_native(
                    '{} {}'.format(
                        shlex.quote(os.path.join(native_source, "configure")),
                        configure_args,
                    ),
                    native_build,
                    "configure",
                )
                self._run_native("make -j1", native_build, "make")
                self._run_native("make check -j1", native_build, "make check")
                self._run_native(
                    "make install DESTDIR={} -j1".format(shlex.quote(native_stage)),
                    native_build,
                    "staged install",
                )
            copy(
                self,
                "COPYING.LIB",
                src=native_source,
                dst=os.path.join(native_stage, "licenses"),
            )
        except Exception:
            self._cleanup_after_error(native_root, "build failure")
            raise

    def package(self):
        native_root = self._native_root()
        native_stage = os.path.join(native_root, "stage")
        self.output.info("native root: {}".format(native_root))
        if not os.path.isdir(native_stage):
            raise ConanException("device-local libassuan package stage is missing")
        try:
            copy(self, "*", src=native_stage, dst=self.package_folder)
        finally:
            self._cleanup_with_warning(native_root, "after package")

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["assuan"]
        self.cpp_info.requires = ["libgpg-error::libgpg-error"]
        self.cpp_info.set_property("pkg_config_name", "libassuan")
        self.cpp_info.set_property("cmake_file_name", "libassuan")
        self.cpp_info.set_property("cmake_target_name", "libassuan::libassuan")

    def _native_root(self):
        identity = repr((self.build_folder, self.package_folder))
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        self.output.info(
            "native identity: build_folder={} package_folder={}".format(
                self.build_folder, self.package_folder
            )
        )
        return os.path.join(
            "/data/storage/el2/base/cache", "libassuan-" + digest
        )

    def _remove_native_root(self, native_root, reason):
        if os.path.exists(native_root):
            shutil.rmtree(native_root)
        if os.path.exists(native_root):
            raise ConanException(
                "failed to remove native root {} {}".format(native_root, reason)
            )

    def _cleanup_after_error(self, native_root, reason):
        try:
            self._remove_native_root(native_root, reason)
        except Exception as cleanup_error:
            self.output.warning(
                "native root cleanup failed after original error: {}".format(
                    cleanup_error
                )
            )

    def _cleanup_with_warning(self, native_root, reason):
        try:
            self._remove_native_root(native_root, reason)
        except Exception as cleanup_error:
            self.output.warning(str(cleanup_error))

    def _run_native(self, command, native_build, step):
        self.output.info("native cwd [{}]: {}".format(step, native_build))
        self.run(command, cwd=native_build)

    def _apply_patches(self, source_folder):
        for entry in self.conan_data.get("patches", []):
            patch_args = entry.copy()
            patch_file = patch_args.pop("patch_file")
            patch(
                self,
                base_path=source_folder,
                patch_file=os.path.join(self.export_sources_folder, patch_file),
                **patch_args,
            )

    @contextmanager
    def _build_environment(self, native_root):
        dependency = self.dependencies["libgpg-error"].package_folder
        dependency_bin = os.path.join(dependency, "bin")
        env = AutotoolsToolchain(self).environment()
        env.compose_env(AutotoolsDeps(self).vars())
        local_env = Environment()
        local_env.define("TMPDIR", os.path.join(native_root, "tmp"))
        local_env.prepend_path("PATH", dependency_bin)
        local_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dependency, "lib"))
        gpgrt_config = os.path.join(dependency_bin, "gpgrt-config")
        gpg_error_config = os.path.join(dependency_bin, "gpg-error-config")
        if os.path.isfile(gpgrt_config):
            local_env.define("GPGRT_CONFIG", gpgrt_config)
        elif os.path.isfile(gpg_error_config):
            local_env.define("GPG_ERROR_CONFIG", gpg_error_config)
        else:
            raise ConanException("libgpg-error package has no usable config script")
        os.makedirs(os.path.join(native_root, "tmp"), exist_ok=True)
        env.compose_env(local_env)
        with env.vars(self).apply():
            yield
