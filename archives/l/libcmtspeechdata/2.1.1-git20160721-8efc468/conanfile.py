from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv
import os
import glob


class LibCmtSpeechDataConan(ConanFile):
    name = "libcmtspeechdata"
    version = "2.1.1-git20160721-8efc468"
    description = "Nokia CMT modem speech data protocol library"
    license = "LGPL-2.1-or-later"
    homepage = "https://sources.debian.org/src/libcmtspeechdata/2.1.1%2Bgit20160721~8efc468-2/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Required by upstream configure, tests, and the D-Bus sound utility.
        self.requires("dbus/1.14.10", visible=False)
        self.requires("pulseaudio/17.0.1", visible=False)
        self.requires("check/0.15.2", visible=False)

    def build_requirements(self):
        # The source archive needs autoreconf, but CI workers do not provide
        # aclocal (and their system autoconf has an incomplete Perl setup).
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-docs",
            "--with-backend=nokiamodem",
        ])
        if self.settings.os == "OHOS":
            # config.guess cannot classify HarmonyOS uname output.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        # The packaged dbus recipe has no dbus-1.pc. The upstream D-Bus
        # utility also uses PulseAudio without declaring its headers/libs.
        dbus_dep = self.dependencies["dbus"]
        dbus = dbus_dep.cpp_info
        dbus_root = dbus_dep.package_folder
        pulse_dep = self.dependencies["pulseaudio"]
        pulse = pulse_dep.cpp_info
        pulse_root = pulse_dep.package_folder
        expat_dep = self.dependencies["expat"]
        expat = expat_dep.cpp_info
        expat_root = expat_dep.package_folder
        env = tc.environment()
        # libcheck probes TEMP before musl P_tmpdir, which points at read-only /tmp.
        env.define("TEMP", self.build_folder)
        check_dep = self.dependencies["check"]
        for libdir in check_dep.cpp_info.libdirs:
            env.prepend_path(
                "LD_LIBRARY_PATH",
                os.path.join(check_dep.package_folder, libdir),
            )
        env.define("DBUS_CFLAGS", " ".join(
            [f"-I{os.path.join(dbus_root, path)}" for path in dbus.includedirs]
            + [f"-I{os.path.join(pulse_root, path)}" for path in pulse.includedirs]
        ))
        pulse_libdirs = list(pulse.libdirs)
        pulse_libdirs += pulse.components["pulsecommon"].libdirs
        env.define("DBUS_LIBS", " ".join(
            [f"-L{os.path.join(dbus_root, path)}" for path in dbus.libdirs]
            + [f"-L{os.path.join(pulse_root, path)}" for path in pulse_libdirs]
            + [f"-L{os.path.join(expat_root, path)}" for path in expat.libdirs]
            + [f"-l{lib}" for lib in dbus.libs]
            + [f"-l{lib}" for lib in expat.libs]
            + [f"-l{lib}" for lib in pulse.components["pulse-simple"].libs]
            + [f"-l{lib}" for lib in pulse.components["pulse"].libs]
            + [f"-l{lib}" for lib in pulse.components["pulsecommon"].libs]
            + [f"-l{lib}" for lib in dbus.system_libs + pulse.system_libs]
        ))
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        if self.options.get_safe("fPIC", True):
            tc.extra_cflags.append("-fPIC")
        tc.generate(env)

    def build(self):
        # Debian's orig tarball has configure.ac but no generated Autotools files.
        # Select Conan's bootstrap tools explicitly: the device system lacks
        # aclocal, and Conan's bundled Perl binary is ABI-incompatible with OHOS.
        autoconf = self.dependencies.build["autoconf"].package_folder
        automake = self.dependencies.build["automake"].package_folder
        libtool = self.dependencies.build["libtool"].package_folder
        tool_path = ":".join(
            os.path.join(root, "bin") for root in (autoconf, automake, libtool)
        )
        automake_perl = os.path.join(automake, "share", "automake-1.18")
        shim_folder = os.path.join(self.build_folder, "autotools-shims")
        os.makedirs(shim_folder, exist_ok=True)
        for tool in ("aclocal", "aclocal-1.18", "automake", "automake-1.18"):
            real_tool = os.path.join(automake, "bin", f".{tool}-real")
            shim = os.path.join(shim_folder, tool)
            if tool.startswith("aclocal"):
                args = (
                    f'--automake-acdir="{os.path.join(automake, "share", "aclocal-1.18")}" '
                    f'--system-acdir="{os.path.join(automake, "share", "aclocal")}" '
                )
            else:
                args = f'--libdir="{automake_perl}" '
            with open(shim, "w", encoding="utf-8") as script:
                script.write(f'#!/bin/sh\nexec "$PERL" "{real_tool}" {args}"$@"\n')
            os.chmod(shim, 0o755)
        aclocal_dirs = [
            os.path.join(automake, "share", "aclocal"),
            os.path.join(automake, "share", "aclocal-1.18"),
            os.path.join(libtool, "share", "aclocal"),
        ]
        aclocal_dirs.extend(glob.glob("/data/service/hnp/*/*/share/aclocal"))
        brew_aclocal = os.path.expanduser("~/.harmonybrew/share/aclocal")
        if os.path.isdir(brew_aclocal):
            aclocal_dirs.append(brew_aclocal)
        aclocal_dirs.append("$ACLOCAL_PATH")
        aclocal_path = ":".join(aclocal_dirs)
        self.run(
            f"PATH={shim_folder}:{tool_path}:$PATH "
            'PERL=$(if [ -x /data/service/hnp/bin/perl ]; then '
            'echo /data/service/hnp/bin/perl; '
            'elif [ -x "$HOME/.harmonybrew/bin/perl" ]; then '
            'echo "$HOME/.harmonybrew/bin/perl"; '
            'elif [ -x /usr/bin/perl ]; then echo /usr/bin/perl; '
            'elif [ -x /usr/local/bin/perl ]; then echo /usr/local/bin/perl; '
            'else command -v perl; fi) '
            f"PERL5LIB={automake_perl} ACLOCAL_PATH={aclocal_path} "
            f"ACLOCAL={os.path.join(shim_folder, 'aclocal')} "
            f"AUTOMAKE={os.path.join(shim_folder, 'automake')} "
            f"{os.path.join(autoconf, 'bin', 'autoreconf')} -fi",
            cwd=self.source_folder,
            env="conanbuild",
        )
        # Autoconf's generated config.status uses umask 077 for confXXXXXX;
        # HMDFS rejects the later subs1.awk write (E011).
        for folder in (self.source_folder, self.build_folder):
            configure = os.path.join(folder, "configure")
            if os.path.isfile(configure):
                with open(configure, encoding="utf-8") as script:
                    contents = script.read()
                contents = contents.replace("umask 077", "umask 022")
                with open(configure, "w", encoding="utf-8") as script:
                    script.write(contents)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Activate Conan's private test runtime env (LD_LIBRARY_PATH and TEMP).
        self.run("make check -j1", cwd=self.build_folder, env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cmtspeechdata"]
        self.cpp_info.set_property("cmake_file_name", "libcmtspeechdata")
        self.cpp_info.set_property("cmake_target_name", "libcmtspeechdata::libcmtspeechdata")
