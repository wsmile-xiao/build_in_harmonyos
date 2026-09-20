from conan import ConanFile
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import shutil
import subprocess


class DarkiceConan(ConanFile):
    name = "darkice"
    version = "1.6"
    description = "DarkIce is a live audio streamer that records audio from an audio interface and sends it to streaming servers"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/rafael2k/darkice"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    generators = "VirtualBuildEnv", "PkgConfigDeps", "AutotoolsDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libogg/1.3.6", override=True)
        self.requires("libvorbis/1.3.7")
        self.requires("opus/1.5.2.1")
        self.requires("flac/1.4.3")
        self.requires("lame/4.0")
        self.requires("alsa-lib/1.2.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        trunk_dir = os.path.join(self.source_folder, "darkice", "trunk")
        if os.path.isdir(trunk_dir):
            for item in os.listdir(trunk_dir):
                src = os.path.join(trunk_dir, item)
                dst = os.path.join(self.source_folder, item)
                if os.path.exists(dst):
                    continue
                os.rename(src, dst)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("ac_cv_prog_cc_crosso=yes")
        tc.configure_args.append("cross_compiling=yes")
        tc.configure_args.append("ac_cv_prog_cc_c_c_o=yes")
        tc.configure_args.append("--with-vorbis")
        tc.configure_args.append("--with-opus")
        tc.configure_args.append("--with-flac")
        tc.configure_args.append("--with-alsa")
        tc.configure_args.append("--with-lame")
        lame_info = self.dependencies.get("lame")
        if lame_info:
            tc.configure_args.append(f"--with-lame-prefix={lame_info.package_folder}")
        tc.configure_args.append("--without-faac")
        tc.configure_args.append("--without-fdkaac")
        tc.configure_args.append("--without-twolame")
        tc.configure_args.append("--without-pulseaudio")
        tc.configure_args.append("--without-jack")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "configure.in")
        dst = os.path.join(self.source_folder, "configure.ac")
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
        self.run("autoconf -f", cwd=self.source_folder, env="conanbuild")
        self.run("sed -i 's/umask 077/umask 022/g' configure",
                 cwd=self.source_folder, env="conanbuild")
        autotools = Autotools(self)
        autotools.configure()
        self.run("sed -i 's|automake-[0-9.]*|true|g' Makefile man/Makefile src/Makefile",
                cwd=self.build_folder, env="conanbuild")
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_binary()

    def _sign_ohos_binary(self):
        bin_path = os.path.join(self.package_folder, "bin", "darkice")
        if not os.path.isfile(bin_path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        for tool in (sign_tool, objcopy):
            if not os.path.isfile(tool):
                return
        subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                       check=False, timeout=10)
        signed_path = f"{bin_path}.signed"
        result = subprocess.run(
            [sign_tool, "sign", "-inFile", bin_path,
             "-outFile", signed_path, "-selfSign", "1"],
            check=False, timeout=15, capture_output=True, text=True
        )
        if result.returncode == 0 and os.path.isfile(signed_path):
            os.replace(signed_path, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
