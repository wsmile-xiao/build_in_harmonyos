#!/usr/bin/env python3
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LinuxPamConan(ConanFile):
    name = "linux-pam"
    version = "1.7.2"
    description = "Pluggable Authentication Modules for Linux"
    license = "BSD-3-Clause OR GPL-2.0-or-later"
    homepage = "https://github.com/linux-pam/linux-pam"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("linux-pam requires a POSIX dynamic-loader environment")
        if not self.options.shared:
            raise ConanInvalidConfiguration("linux-pam modules and consumers require shared libraries")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["i18n"] = "disabled"
        tc.project_options["docs"] = "disabled"
        tc.project_options["audit"] = "disabled"
        tc.project_options["econf"] = "disabled"
        tc.project_options["logind"] = "disabled"
        tc.project_options["elogind"] = "disabled"
        tc.project_options["openssl"] = "disabled"
        tc.project_options["pwaccess"] = "disabled"
        tc.project_options["selinux"] = "disabled"
        tc.project_options["nis"] = "disabled"
        tc.project_options["examples"] = "false"
        tc.project_options["xtests"] = "false"
        tc.project_options["lckpwdf"] = "false"
        tc.project_options["pam_userdb"] = "disabled"
        tc.project_options["pam_lastlog"] = "disabled"
        tc.project_options["pam_unix"] = "disabled"
        tc.project_options["vendordir"] = ""
        tc.generate()
        self._inject_meson_archiver()

    def build(self):
        apply_conandata_patches(self)
        self._make_upstream_test_helpers_executable()
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._materialize_shared_library_aliases(os.path.join(self.build_folder, "libpam"))

        def _meson_test_print_errorlogs():
            self.run('meson test -C "{}" --print-errorlogs'.format(self.build_folder))

        meson.test = _meson_test_print_errorlogs
        meson.test()

    def _make_upstream_test_helpers_executable(self):
        for path in glob.glob(os.path.join(self.source_folder, "aux", "*.sh")):
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "Copyright", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        self._materialize_shared_library_aliases(os.path.join(self.package_folder, "lib"))
        if str(self.settings.os) == "OHOS":
            self._sign_shared_objects()

    def _materialize_shared_library_aliases(self, libdir):
        aliases = {
            "libpam.so.0.85.1": ["libpam.so.0", "libpam.so"],
            "libpam_misc.so.0.82.1": ["libpam_misc.so.0", "libpam_misc.so"],
            "libpamc.so.0.82.1": ["libpamc.so.0", "libpamc.so"],
        }
        for real_name, alias_names in aliases.items():
            src = os.path.join(libdir, real_name)
            if not os.path.isfile(src):
                continue
            for alias_name in alias_names:
                dst = os.path.join(libdir, alias_name)
                if os.path.exists(dst):
                    continue
                shutil.copy2(src, dst)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "linux-pam")

        pam = self.cpp_info.components["pam"]
        pam.libs = ["pam"]
        pam.system_libs = ["dl"]
        pam.set_property("cmake_target_name", "linux-pam::pam")
        pam.set_property("pkg_config_name", "pam")

        pam_misc = self.cpp_info.components["pam_misc"]
        pam_misc.libs = ["pam_misc"]
        pam_misc.requires = ["pam"]
        pam_misc.set_property("cmake_target_name", "linux-pam::pam_misc")
        pam_misc.set_property("pkg_config_name", "pam_misc")

        pamc = self.cpp_info.components["pamc"]
        pamc.libs = ["pamc"]
        pamc.set_property("cmake_target_name", "linux-pam::pamc")
        pamc.set_property("pkg_config_name", "pamc")

        libdir = os.path.join(self.package_folder, "lib")
        self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)
        self.buildenv_info.append_path("LD_LIBRARY_PATH", libdir)
        self.runenv_info.define_path("LINUX_PAM_MODULE_DIR", os.path.join(libdir, "security"))
        self.buildenv_info.define_path("LINUX_PAM_MODULE_DIR", os.path.join(libdir, "security"))

    def _inject_meson_archiver(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("c") or executables.get("cpp") or ""
            bindir = os.path.dirname(compiler)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        binaries = "[binaries]\nar = '%s'\n" % ar
        if ranlib:
            binaries += "ranlib = '%s'\n" % ranlib
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", binaries, 1))

    def _sign_shared_objects(self):
        objcopy = self._find_ohos_tool("OHOS_LLVM_OBJCOPY", "llvm-objcopy")
        signer = self._find_ohos_tool("OHOS_BINARY_SIGN_TOOL", "binary-sign-tool")
        missing = [
            name
            for name, path in (("llvm-objcopy", objcopy), ("binary-sign-tool", signer))
            if not path
        ]
        if missing:
            raise ConanException("OHOS signing tools unavailable: %s" % ", ".join(missing))
        patterns = [
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        for pattern in patterns:
            for path in glob.glob(pattern, recursive=True):
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                strip_result = self.run(
                    f'{objcopy} --remove-section .codesign "{path}"',
                    ignore_errors=True,
                )
                if strip_result != 0:
                    raise ConanException(
                        "llvm-objcopy could not remove .codesign from %s" % path
                    )
                sign_result = self.run(
                    f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1',
                    ignore_errors=True,
                )
                if sign_result != 0:
                    raise ConanException("binary-sign-tool failed for %s" % path)

    @staticmethod
    def _find_ohos_tool(env_name, command):
        configured = os.environ.get(env_name)
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.isfile(configured):
                return configured
        tool_dir = os.environ.get("SIGN_TOOL_PATH")
        if tool_dir:
            candidate = os.path.join(tool_dir, command)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(command)
