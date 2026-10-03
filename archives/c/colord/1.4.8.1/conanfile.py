from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
import json
import os
import re
import shutil

required_conan_version = ">=2.28"


class ColordConan(ConanFile):
    name = "colord"
    version = "1.4.8.1"
    description = "colord is a system daemon for managing color devices"
    license = "LGPL-2.1+"
    homepage = "https://github.com/hughsie/colord"
    url = "https://github.com/hughsie/colord"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options["glib2"].shared = True

    def requirements(self):
        self.requires("glib2/2.88.0", transitive_headers=True, transitive_libs=True)
        self.requires("lcms2/2.19", transitive_headers=True)
        self.requires("sqlite3/3.53.4")

    def build_requirements(self):
        # System meson (1.11.x) and ninja (1.13.x) available in PATH
        # No conan tool_requires needed for meson/ninja
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Fix toolchain: CI workers export llvm-* bare names that meson can't find
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}")

        # Ensure meson can find ninja backend via NINJA env var
        ninja_path = shutil.which("ninja")
        if not ninja_path:
            raise ConanInvalidConfiguration("ninja not found in PATH")

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.binaries["ninja"] = ninja_path

        # Project options: disable features not applicable to OHOS
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["daemon"] = "false"
        tc.project_options["systemd"] = "false"
        tc.project_options["udev_rules"] = "false"
        tc.project_options["introspection"] = "false"
        tc.project_options["man"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["bash_completion"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["sane"] = "false"
        tc.project_options["session_example"] = "false"
        tc.project_options["print_profiles"] = "false"
        tc.project_options["argyllcms_sensor"] = "false"
        tc.project_options["libcolordcompat"] = "false"
        # 1.4.8.1: enable the upstream self-test suite (colord-test-private).
        # colord-test-daemon is registered only when the daemon option is on
        # (see patches/0002), because it needs a running colord daemon over a
        # D-Bus session bus which does not exist on OHOS.
        tc.project_options["tests"] = "true"
        tc.project_options["installed_tests"] = "false"
        tc.generate()

        # Write compat .pc files for glib2 sub-modules
        self._write_compat_pc_files()

        # Inject NINJA env var into build environment so meson's detect_ninja can find it
        from conan.tools.env import Environment
        env = Environment()
        env.define("NINJA", ninja_path)
        # ninja (and other host tools) need libc++_shared.so which is in a
        # subdirectory not covered by the default LD_LIBRARY_PATH in the profile.
        # Add it so ninja can execute during meson's ninja version detection.
        libcxx_dir = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        if os.path.isdir(libcxx_dir):
            env.prepend_path("LD_LIBRARY_PATH", libcxx_dir)
        env.vars(self, scope="build").save_script("colord_ninja_env")

    def _write_compat_pc_files(self):
        """Write pkg-config shim files for glib2 sub-modules.

        The glib2 Conan package only generates a combined glib-2.0.pc.
        Meson's dependency('gio-2.0'|'gobject-2.0'|'gio-unix-2.0'|
        'gmodule-2.0') looks for individual .pc files.
        """
        glib = self.dependencies["glib2"].package_folder
        gens = self.generators_folder

        # Patch glib-2.0.pc with tool variables and libintl.h include path
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            with open(glib_pc, encoding="utf-8") as f:
                content = f.read()
            if "glib_genmarshal" not in content:
                content += (
                    "\nglib_genmarshal={gb}/bin/glib-genmarshal\n"
                    "glib_mkenums={gb}/bin/glib-mkenums\n"
                ).format(gb=glib)
            with open(glib_pc, "w", encoding="utf-8") as f:
                f.write(content)

        # Write individual module .pc files as thin wrappers around glib-2.0
        for name, desc in (
            ("gobject-2.0", "GLib Type, Object, Parameter and Signal Library"),
            ("gio-2.0", "glib I/O library"),
            ("gio-unix-2.0", "GLib Unix I/O library"),
            ("gmodule-2.0", "Dynamic module loader for GLib"),
        ):
            with open(os.path.join(gens, f"{name}.pc"), "w", encoding="utf-8") as f:
                f.write(
                    "prefix={glib}\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                    "\n"
                    "Name: {name}\n"
                    "Description: {desc}\n"
                    "Version: 2.88.0\n"
                    "Requires: glib-2.0\n"
                    "Libs: -L\"${{libdir}}\"\n"
                    "Cflags: -I\"${{includedir}}\" -I\"${{includedir}}/glib-2.0\" -I\"${{includedir1}}\"\n"
                    .format(name=name, desc=desc, glib=glib))

    def _run_upstream_tests(self, meson):
        """Run the upstream meson test suite (colord-test-private) and emit
        the HMBS_UPSTREAM_TEST_RESULT marker with real numbers parsed from
        the meson framework summary (Ok:/Fail:/Skipped:/Timeout:/Not run:).

        The OHOS device has a read-only /tmp, so point TMPDIR at a writable
        directory inside the conan build folder (patches/0002 makes the
        self-test code honour g_get_tmp_dir() instead of hardcoding /tmp).
        """
        os.makedirs(os.path.join(self.build_folder, "tmp"), exist_ok=True)
        os.environ["TMPDIR"] = os.path.join(self.build_folder, "tmp")
        log_path = os.path.join(self.build_folder, "meson_test.log")
        test_cmd = (
            'meson test -C "{bdir}" --no-rebuild --print-errorlogs '
            '> "{log}" 2>&1'
        ).format(bdir=self.build_folder, log=log_path)
        self.output.info("=== running upstream meson tests ===")
        self.run(test_cmd, ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("=== upstream meson test (tail) ===")
        for line in (out.splitlines() or [])[-30:]:
            self.output.info(line)

        def _cnt(pat):
            m = re.search(pat, out, flags=re.MULTILINE)
            return int(m.group(1)) if m else 0

        ok = _cnt(r"^Ok:\s+(\d+)")
        fail = _cnt(r"^Fail:\s+(\d+)")
        skipped = _cnt(r"^Skipped:\s+(\d+)")
        timeout = _cnt(r"^Timeout:\s+(\d+)")
        not_run = _cnt(r"^Not run:\s+(\d+)")
        executed = ok + fail + skipped + timeout + not_run
        passed = ok
        ut_result = {
            "status": "passed" if (executed > 0 and fail == 0 and timeout == 0 and not_run == 0) else "failed",
            "framework": "meson",
            "command": test_cmd,
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": fail,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result, ensure_ascii=False)
        )
        if fail > 0 or timeout > 0 or not_run > 0:
            raise RuntimeError(
                "upstream meson tests failed: executed=%d passed=%d failed=%d skipped=%d"
                % (executed, passed, fail, skipped)
            )

    def build(self):
        apply_conandata_patches(self)
        # Set NINJA env var so meson's detect_ninja finds it
        ninja_path = shutil.which("ninja")
        if ninja_path:
            os.environ["NINJA"] = ninja_path

        # Use Conan's Meson class for configure and build
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Run the upstream self-test suite (colord-test-private). The daemon
        # test (colord-test-daemon) is not registered because it requires a
        # running colord daemon over a D-Bus session bus (OHOS has neither).
        self._run_upstream_tests(meson)

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._resign_elf()

    def _resign_elf(self):
        """Re-sign ELF binaries after meson install.

        Meson builds shared libraries and CLI tools with linker self-signing.
        OHOS requires proper ELF signing via binary-sign-tool for execution.
        Strip old .codesign and re-sign (same approach as at-spi2-core).
        """
        import glob
        hnp = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp, "llvm-objcopy")
        signer = os.path.join(hnp, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("binary-sign-tool/llvm-objcopy not available, skipping ELF re-sign")
            return
        elfs = []
        for pat in ("bin/*", "lib/*.so.*"):
            elfs += glob.glob(os.path.join(self.package_folder, pat))
        for f in sorted(set(elfs)):
            if not os.path.isfile(f) or os.path.islink(f):
                continue
            try:
                if open(f, "rb").read(4) != b"\x7fELF":
                    continue
            except OSError:
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}.signed" -selfSign 1'.format(sg=signer, f=f))
            if os.path.isfile(f + ".signed"):
                os.replace(f + ".signed", f)
                os.chmod(f, 0o755)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "colord")
        self.cpp_info.libs = ["colord", "colordprivate"]
        self.cpp_info.includedirs = ["include/colord-1"]
        self.cpp_info.requires = ["glib2::glib2", "lcms2::lcms2", "sqlite3::sqlite3"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # colormgr and other CLI tools installed to bin/
        self.cpp_info.bindirs = ["bin"]
        # Shared libraries need LD_LIBRARY_PATH for runtime
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # libc++_shared.so needed by colord shared libs (linked against libc++)
        libcxx_dir = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        if os.path.isdir(libcxx_dir):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", libcxx_dir)
