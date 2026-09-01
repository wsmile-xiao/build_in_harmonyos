from conan import ConanFile
from conan.tools.files import get, save, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
import os


class PulseaudioConan(ConanFile):
    name = "pulseaudio"
    version = "17.0.1"
    description = "PulseAudio sound server — client libraries for audio playback and recording"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/PulseAudio/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libsndfile/1.2.2")
        self.requires("glib/2.88.0")
        self.requires("check/0.15.2")  # Required for tests=true (upstream test framework)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # Create .tarball-version for meson version detection
        tbv = os.path.join(self.source_folder, ".tarball-version")
        with open(tbv, "w") as f:
            f.write("17.0\n")

        # Hardcode version in meson.build (git-version-gen fails on OHOS
        # due to posix_spawn PATH resolution issue)
        mb = os.path.join(self.source_folder, "meson.build")
        with open(mb, "r") as f:
            content = f.read()
        content = content.replace(
            "version : run_command(find_program('git-version-gen'), "
            "join_paths(meson.current_source_dir(), '.tarball-version'), "
            "check : false).stdout().strip(),",
            "version : '17.0',"
        )
        with open(mb, "w") as f:
            f.write(content)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["tests"] = True
        tc.project_options["doxygen"] = False
        tc.project_options["man"] = False
        tc.project_options["daemon"] = False
        tc.project_options["database"] = "simple"
        tc.project_options["bluez5"] = "disabled"
        tc.project_options["avahi"] = "disabled"
        tc.project_options["jack"] = "disabled"
        tc.project_options["lirc"] = "disabled"
        tc.project_options["openssl"] = "disabled"
        tc.project_options["systemd"] = "disabled"
        tc.project_options["udev"] = "disabled"
        tc.project_options["consolekit"] = "disabled"
        tc.project_options["elogind"] = "disabled"
        tc.project_options["hal-compat"] = False
        tc.project_options["tcpwrap"] = "disabled"
        tc.project_options["valgrind"] = "disabled"
        tc.project_options["gstreamer"] = "disabled"
        tc.project_options["gtk"] = "disabled"
        tc.project_options["gsettings"] = "disabled"
        tc.project_options["webrtc-aec"] = "disabled"
        tc.project_options["orc"] = "disabled"
        tc.project_options["soxr"] = "disabled"
        tc.project_options["speex"] = "disabled"
        tc.project_options["fftw"] = "disabled"
        tc.project_options["asyncns"] = "disabled"
        tc.project_options["oss-output"] = "disabled"
        tc.project_options["ipv6"] = False
        tc.project_options["glib"] = "enabled"
        tc.project_options["x11"] = "disabled"
        tc.generate()
        # Generate .pc files for dependencies (meson uses pkg-config)
        pgd = PkgConfigDeps(self)
        pgd.generate()

        # R33: On OHOS, meson posix_spawn cannot resolve binaries via PATH.
        # Patch the conan-generated native file to add full binary paths,
        # and create a cross file from it.
        if self.settings.os in ("Linux", "OHOS"):
            native_path = os.path.join(self.generators_folder, "conan_meson_native.ini")
            if os.path.exists(native_path):
                with open(native_path, "r") as f:
                    native_content = f.read()

                bin_paths = (
                    "ar = '/data/service/hnp/bin/llvm-ar'\n"
                    "ranlib = '/data/service/hnp/bin/llvm-ranlib'\n"
                    "strip = '/data/service/hnp/bin/llvm-strip'\n"
                    "nm = '/data/service/hnp/bin/llvm-nm'\n"
                    "ld = '/data/service/hnp/binutils.org/binutils_2.45/bin/ld'\n"
                    "objcopy = '/data/service/hnp/bin/llvm-objcopy'\n"
                    "pkg-config = '/data/service/hnp/bin/pkg-config'\n"
                )
                ld_opt = "--ld-path=/data/service/hnp/binutils.org/binutils_2.45/bin/ld"

                # Insert binary paths into existing [binaries] section
                patched_native = native_content.replace(
                    "[binaries]\n",
                    f"[binaries]\n{bin_paths}"
                )
                # Add ld-path to existing c_link_args (if exists) or create new
                if "c_link_args" in patched_native:
                    # Append --ld-path to existing c_link_args value
                    import re
                    patched_native = re.sub(
                        r"(c_link_args\s*=\s*\[)",
                        rf"\1'{ld_opt}', ",
                        patched_native
                    )
                elif "[built-in options]" in patched_native:
                    patched_native = patched_native.replace(
                        "[built-in options]",
                        f"[built-in options]\nc_link_args = ['{ld_opt}']\n"
                    )
                else:
                    patched_native += (
                        f"\n[built-in options]\n"
                        f"c_link_args = ['{ld_opt}']\n"
                    )
                with open(native_path, "w") as f:
                    f.write(patched_native)

                # Create cross file from patched native + exe_wrapper + host_machine
                cross_content = patched_native
                if "exe_wrapper" not in cross_content:
                    # Add exe_wrapper after [binaries] section
                    cross_content = cross_content.replace(
                        "objcopy = '/data/service/hnp/bin/llvm-objcopy'\n",
                        "objcopy = '/data/service/hnp/bin/llvm-objcopy'\n"
                        "exe_wrapper = ['echo', 'SKIP']\n"
                    )
                cross_content += (
                    "\n[host_machine]\n"
                    "system = 'linux'\n"
                    "cpu_family = 'aarch64'\n"
                    "cpu = 'aarch64'\n"
                    "endian = 'little'\n"
                )
                save(self, "ohos_cross.ini", cross_content)

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os in ("Linux", "OHOS"):
            gen_dir = self.generators_folder
            native_file = os.path.join(gen_dir, "conan_meson_native.ini")
            cross_file = os.path.join(gen_dir, "ohos_cross.ini")
            opts = " ".join([
                "-Dtests=true", "-Ddoxygen=false", "-Dman=false",
                "-Ddaemon=false", "-Ddatabase=simple",
                "-Dbluez5=disabled", "-Davahi=disabled", "-Djack=disabled",
                "-Dlirc=disabled", "-Dopenssl=disabled", "-Dsystemd=disabled",
                "-Dudev=disabled", "-Dconsolekit=disabled", "-Delogind=disabled",
                "-Dhal-compat=false", "-Dtcpwrap=disabled", "-Dvalgrind=disabled",
                "-Dgstreamer=disabled", "-Dgtk=disabled", "-Dgsettings=disabled",
                "-Dwebrtc-aec=disabled", "-Dorc=disabled", "-Dsoxr=disabled",
                "-Dspeex=disabled", "-Dfftw=disabled", "-Dasyncns=disabled",
                "-Doss-output=disabled", "-Dipv6=false",
                "-Dglib=enabled", "-Dx11=disabled",
            ])
            self.run(
                f'meson setup "{self.build_folder}" "{self.source_folder}" '
                f'--prefix=/ '
                f'--native-file "{native_file}" '
                f'--cross-file "{cross_file}" '
                f'{opts}',
                env="conanbuild"
            )
            self.run(f'ninja -C "{self.build_folder}" -j1', env="conanbuild")
        else:
            meson = Meson(self)
            meson.configure()
            meson.build(args=["-j1"])

    def package(self):
        if self.settings.os in ("Linux", "OHOS"):
            self.run(
                f'DESTDIR="{self.package_folder}" ninja -C "{self.build_folder}" install',
                env="conanbuild"
            )
        else:
            meson = Meson(self)
            meson.install()

    def package_info(self):
        # R32: settings.os must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl", "rt"]

        # Main client library
        pulse = self.cpp_info.components["pulse"]
        pulse.libs = ["pulse"]
        pulse.requires = ["pulsecommon"]

        # Simple API wrapper
        pulse_simple = self.cpp_info.components["pulse-simple"]
        pulse_simple.libs = ["pulse-simple"]
        pulse_simple.requires = ["pulse"]

        # GLib mainloop integration
        pulse_glib = self.cpp_info.components["pulse-mainloop-glib"]
        pulse_glib.libs = ["pulse-mainloop-glib"]
        pulse_glib.requires = ["pulse"]

        # Common library (installed in lib/pulseaudio/)
        pulsecommon = self.cpp_info.components["pulsecommon"]
        pulsecommon.libs = ["pulsecommon-17.0"]
        # Add libdirs for the pulsecommon library location
        pulsecommon.libdirs.append(os.path.join("lib", "pulseaudio"))
