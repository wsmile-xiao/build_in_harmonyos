import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SerdConan(ConanFile):
    name = "serd"
    version = "0.32.9"
    description = "Lightweight C library for working with RDF data"
    license = "ISC"
    homepage = "https://drobilla.net/software/serd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["checks"] = "enabled"
        tc.project_options["docs"] = "disabled"
        tc.project_options["html"] = "disabled"
        tc.project_options["lint"] = "false"
        tc.project_options["man"] = "disabled"
        tc.project_options["man_html"] = "disabled"
        tc.project_options["singlehtml"] = "disabled"
        tc.project_options["tests"] = "enabled"
        tc.project_options["tools"] = "enabled"
        tc.generate()
        self._inject_meson_archiver()

    def build(self):
        self._prepare_ohos_test_commands()
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info("cross-building: skip meson.test()")
        else:
            meson.test()

    def package(self):
        Meson(self).install()
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_serdi()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses", "LICENSES"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["serd-0"]
        self.cpp_info.includedirs = ["include/serd-0"]
        self.cpp_info.set_property("cmake_file_name", "serd")
        self.cpp_info.set_property("cmake_target_name", "serd::serd")
        self.cpp_info.set_property("pkg_config_name", "serd-0")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _prepare_ohos_test_commands(self):
        if str(self.settings.os) != "OHOS":
            return

        tests = os.path.join(self.source_folder, "test", "meson.build")
        replace_in_file(
            self,
            tests,
            "run_suite = find_program('run_suite.py')",
            "python = import('python').find_installation()\n"
            "run_suite = files('run_suite.py')",
        )
        replace_in_file(
            self,
            tests,
            "    files('test_quiet.py'),\n"
            "    args: script_args + [bad_input_file],",
            "    python,\n"
            "    args: files('test_quiet.py') + script_args + [bad_input_file],",
        )
        replace_in_file(
            self,
            tests,
            "  test('stdin', files('test_stdin.py'), args: script_args, suite: input_suite)",
            "  test('stdin', python, args: files('test_stdin.py') + script_args, "
            "suite: input_suite)",
        )
        replace_in_file(
            self,
            tests,
            "    files('test_write_error.py'),\n"
            "    args: script_args + [serd_ttl],",
            "    python,\n"
            "    args: files('test_write_error.py') + script_args + [serd_ttl],",
        )
        replace_in_file(
            self,
            tests,
            "      run_suite,\n"
            "      args: script_args + args,",
            "      python,\n"
            "      args: run_suite + script_args + args,",
        )

    def _inject_meson_archiver(self):
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if not ar:
            cc = compiler_exes.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate

        if not ar:
            return

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content or "\nar =" in content:
                continue
            insertion = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
            if ranlib:
                insertion += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content.replace("[binaries]\n", insertion, 1))

    def _sign_ohos_serdi(self):
        serdi = os.path.join(self.package_folder, "bin", "serdi")
        if not os.path.isfile(serdi):
            return

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("OHOS signing tools not found; skip serdi signing")
            return

        signed = serdi + ".signed"
        self.run(f'"{objcopy}" --remove-section .codesign "{serdi}" 2>/dev/null || true')
        self.run(f'"{signer}" sign -inFile "{serdi}" -outFile "{signed}" -selfSign 1')
        os.replace(signed, serdi)
        os.chmod(serdi, 0o755)
