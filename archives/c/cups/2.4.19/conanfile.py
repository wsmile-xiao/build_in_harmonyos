#!/usr/bin/env python3
"""Conan recipe for CUPS 2.4.19 using Autotools."""

import os

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


_LN_COPY = r"""#!/system/bin/sh
set -u

while [ "$#" -gt 0 ]; do
  case "$1" in
    -s|-f|-sf|-fs)
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

if [ "$#" -lt 2 ]; then
  echo "ln-copy: expected SOURCE... DEST" >&2
  exit 2
fi

dest_path=
for argument in "$@"; do
  dest_path=$argument
done

while [ "$#" -gt 1 ]; do
  source_path=$1
  shift

  if [ -d "$dest_path" ]; then
    final_path="$dest_path/$(basename "$source_path")"
  else
    final_path=$dest_path
  fi

  case "$source_path" in
    /*)
      resolved_path=$source_path
      ;;
    *)
      resolved_path="$(dirname "$final_path")/$source_path"
      ;;
  esac

  if [ -d "$resolved_path" ]; then
    cp -Rp "$resolved_path" "$final_path" || exit 1
  elif [ -f "$resolved_path" ]; then
    cp -p "$resolved_path" "$final_path" || exit 1
  else
    echo "ln-copy: missing source $source_path" >&2
    exit 1
  fi
done
"""


class CupsConan(ConanFile):
    name = "cups"
    version = "2.4.19"
    description = "OpenPrinting CUPS printing system and IPP library"
    license = "Apache-2.0"
    homepage = "https://openprinting.github.io/cups/"
    url = "https://github.com/OpenPrinting/cups"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1.1")
        self.requires("libiconv/1.17")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-components=all",
            "--with-tls=openssl",
            "--with-dnssd=no",
            "--disable-libusb",
            "--disable-dbus",
            "--disable-pam",
            "--disable-gssapi",
            "--disable-libpaper",
            "--disable-acl",
            "--disable-tcp-wrappers",
            "--with-rcdir=no",
        ])
        if self.settings.os == "OHOS":
            tc.configure_args.append(
                f"--with-shell-script-fallback={self._shell}"
            )
        tc.generate()

    @property
    def _shell(self):
        return "/system/bin/sh" if self.settings.os == "OHOS" else "/bin/sh"

    @property
    def _ln_copy(self):
        return os.path.join(self.build_folder, "conan-ln-copy.sh")

    @property
    def _tmpdir(self):
        if self.settings.os == "OHOS":
            return os.environ.get("TMPDIR") or "/data/storage/el2/base/cache"
        return os.path.join(self.build_folder, "tmp")

    def _write_ln_copy(self):
        script = _LN_COPY if self.settings.os == "OHOS" else _LN_COPY.replace(
            "#!/system/bin/sh", "#!/bin/sh", 1
        )
        save(self, self._ln_copy, script)

    def _dso_environment(self):
        lib_flags = []
        for dependency in self.dependencies.host.values():
            lib_flags.extend(f"-L{libdir}" for libdir in dependency.cpp_info.libdirs)
        # OHOS Conan build folders can be HMDFS-backed; keep scratch on system temp.
        tmpdir = self._tmpdir
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("DSOFLAGS", " ".join(dict.fromkeys(lib_flags)))
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.define("TMPPREFIX", os.path.join(tmpdir, "zsh"))
        return env

    def _make_args(self):
        ln_copy = f"{self._shell} {self._ln_copy}"
        return ["-j1", f"SHELL={self._shell}", f'LN="{ln_copy}"']

    def _run_make(self, *args):
        make_program = self.conf.get("tools.gnu:make_program", default="make")
        command = " ".join([f'"{make_program}"', *self._make_args(), *args])
        self.run(command, cwd=self.source_folder)

    def _configure(self):
        toolchain = load_toolchain_args(self.generators_folder)
        configure_args = toolchain.get("configure_args", "")
        configure = os.path.join(self.source_folder, "configure")
        tmpdir = self._tmpdir
        configure_environment = [
            ("CONFIG_SHELL", self._shell),
            ("SHELL", self._shell),
            ("TMPDIR", tmpdir),
            ("TMP", tmpdir),
            ("TEMP", tmpdir),
            ("PKG_CONFIG_PATH", self.generators_folder),
        ]
        if self.settings.os == "OHOS":
            configure_environment.extend([
                ("ac_cv_func_symlink", "no"),
                ("ac_cv_func_pthread_cancel", "no"),
                ("ac_cv_func_getspnam", "no"),
                ("ac_cv_func_endspent", "no"),
            ])

        command_env = " ".join(
            f'{name}="{value}"'
            for name, value in configure_environment
        )
        # conanbuild is sourced after Environment.apply(), so override its shell here.
        self.run(
            f'{command_env} "{self._shell}" "{configure}" {configure_args}',
            cwd=self.source_folder,
        )

    def build(self):
        apply_conandata_patches(self)
        self._write_ln_copy()
        with self._dso_environment().vars(self).apply():
            self._configure()
            self._run_make("check")

    def package(self):
        install_script = f"{self._shell} {os.path.join(self.source_folder, 'install-sh')}"
        if self.settings.os == "OHOS":
            install = "/bin/install"
        else:
            install = install_script
        install_executable = f"{install} -c -m 755"
        install_args = [
            f'DESTDIR="{self.package_folder}"',
            f'INSTALL="{install}"',
            f'INSTALL_BIN="{install_executable}"',
            f'INSTALL_LIB="{install_executable}"',
        ]
        if self.settings.os == "OHOS":
            install_args.extend([
                f'INSTALL_COMPDATA="{install_script} -c -m 444 -z"',
                f"CUPS_USER={os.getuid()}",
                f"CUPS_GROUP={os.getgid()}",
                f"CUPS_PRIMARY_SYSTEM_GROUP={os.getgid()}",
            ])
        install_args.append("install")
        with self._dso_environment().vars(self).apply():
            self._run_make(*install_args)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["usr/include"]
        self.cpp_info.libs = ["cupsimage", "cups"]
        self.cpp_info.system_libs = ["pthread", "dl"]
        self.cpp_info.set_property("cmake_file_name", "cups")
        self.cpp_info.set_property("cmake_target_name", "cups::cups")
        self.cpp_info.set_property("pkg_config_name", "cups")
