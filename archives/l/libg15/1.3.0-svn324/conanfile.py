#!/usr/bin/env python3
"""Conan recipe for libg15 1.3.0-svn324 — Logitech G11/G15 keyboard library.

Upstream: Debian's official git hosting (salsa.debian.org/debian/libg15),
tag debian/1.3.0_svn324-2 == the 1.3.0~svn324 orig tarball (R39 official
hosting exception, see notes.md). autotools; the tree ships only
configure.in + bootstrap (no pre-generated configure), so source() runs
bootstrap (aclocal/libtoolize/autoheader/automake/autoconf) to produce it.

The upstream code targets the legacy libusb-0.1 API; Debian patches
01/02 (shipped in patches/) migrate it to libusb-1.0 — required because the
recipe depends on libusb/1.0.27. Patched configure.in does
AC_CHECK_LIB([usb-1.0]) + AC_CHECK_HEADERS([libusb-1.0/libusb.h]); no
platform macros are introduced (R8).

OHOS/HMDFS adaptation notes:
- autoconf's config.status builds its temp dirs with
  `(umask 077 && mktemp -d ./confXXXXXX)`; on the OHOS PC shared filesystem
  a 0700-mode dir (→2700 after setgid inheritance) is not writable by the
  build uid when the tree is shared, so config.status dies with
  "can't create ./conf*/subs1.awk: Permission denied". Rewrite umask
  077 -> 022 in the generated configure so temp dirs stay group-writable
  (same fix as archives/l/libusb/1.0.27).
- the aclocal installed on the build box embeds a literal '@am_AUTOM4TE@'
  (unsubstituted automake template), so AUTOM4TE is exported to the real
  autom4te during bootstrap.
- config.guess identifies this platform as aarch64-unknown-linux-ohos, so
  no --host/--build override is needed (native build, R32: recipe logic uses
  in ("Linux", "OHOS")).
- CI 的 automake 由 tool_requires 提供（automake/1.18，config.guess
  2024-07-27）：该代脚本主 case 无 HarmonyOS 分支，在 OHOS 上会落到
  dummy.c 临时探测段（umask 077 的 $TMPDIR/cgXXXXXX 在 HMDFS 共享缓存上
  setgid 继承后不可写）→ "dummy.c: Permission denied" → "cannot guess
  build type"。本地回退到系统 automake 1.16（其 config.guess 2023-08-22
  自带 HarmonyOS 分支）所以本地通过、CI 失败。build() 在 bootstrap 后注入
  HarmonyOS 分支（E007/E160 模式），使 config.guess 直接输出三元组并
  退出、完全不触碰临时目录；config.sub 2024 已认 linux-ohos，无需改动。

No upstream test suite: Makefile.am defines no TESTS/check_PROGRAMS and
`make check` is an empty no-op (R51 evidence in notes.md). test_package/
verifies link + initLibG15() return code (no G15 hardware on OHOS ->
G15_ERROR_OPENING_USB_DEVICE is the expected hardware-independent result).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rm
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libg15Conan(ConanFile):
    name = "libg15"
    version = "1.3.0-svn324"
    description = ("Library for interfacing with the Logitech G11/G15 keyboards "
                   "(LCD, extra keys, LEDs)")
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/debian/libg15"
    url = "https://salsa.debian.org/debian/libg15"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def build_requirements(self):
        # tarball 只含 configure.in + bootstrap（无预生成 configure），build()
        # 必须跑 aclocal/libtoolize/autoheader/automake/autoconf 生成。
        # CI worker（USER=100）看不到 $HOME/usr/local/bin 下手装的
        # automake/libtool（0770 属主跨 UID 不可执行，E443），且
        # /data/service/hnp/bin 只有 autoconf 族 —— aclocal/automake 会
        # "not found"。由 tool_requires 提供（registry 有 1.18/2.5.4），
        # VirtualBuildEnv 把其 bin 注入 conanbuild PATH（centerim5/zzuf
        # 同型先例，E540）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # Only upstream code is needed; the Debian/rpm packaging dirs in the
        # salsa archive are not part of the build and would just add noise.
        rm(self, "debian", self.source_folder, recursive=True)
        rm(self, "rpm", self.source_folder, recursive=True)
        # bootstrap 不在 source() 跑：autotools 工具链由 build_requirements
        # 的 tool_requires 提供，只在 build() 的 conanbuild 环境可用
        # （centerim5/zzuf 同型先例）。

    def _generate_configure(self):
        """Run upstream ./bootstrap to produce configure (autotools regen).

        Runs inside the conanbuild env so tool_requires(automake/libtool)
        bin dirs are on PATH (VirtualBuildEnv; centerim5/zzuf precedent)."""
        autom4te = self._find_autom4te()
        os.makedirs(os.path.join(self.source_folder, "config"), exist_ok=True)
        cmd = "sh ./bootstrap"
        if autom4te:
            cmd = "AUTOM4TE={!r} sh ./bootstrap".format(autom4te)
        self.run(cmd, cwd=self.source_folder, env="conanbuild")
        for marker in ("configure", "Makefile.in", "config.h.in"):
            path = os.path.join(self.source_folder, marker)
            if not os.path.isfile(path):
                raise ConanException(
                    "bootstrap did not generate {}".format(marker))

    @staticmethod
    def _find_autom4te():
        exe = shutil.which("autom4te")
        if exe:
            return exe
        for cand in ("/storage/Users/currentUser/usr/local/bin/autom4te",
                     "/usr/local/bin/autom4te", "/usr/bin/autom4te",
                     "/data/service/hnp/bin/autom4te"):
            if os.path.isfile(cand):
                return cand
        return None

    def _fix_configure_umask(self):
        """HMDFS: config.status temp dirs created with umask 077 become 0700
        (setgid-inherited 2700) and are unwritable by the build uid on the
        shared filesystem -> 'subs1.awk: Permission denied'. Force 022."""
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(
            self, configure,
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null`')
        replace_in_file(
            self, configure,
            '(umask 077 && mkdir "$tmp")',
            '(umask 022 && mkdir "$tmp")')

    def _fix_config_guess_ohos(self):
        """CI tool_requires automake/1.18 的 config.guess（2024-07-27）主 case
        无 HarmonyOS 分支：OHOS 上落到尾部 dummy.c 探测段（umask 077 建
        $TMPDIR/cgXXXXXX，HMDFS 共享缓存 setgid 继承后跨 UID 不可写）→
        "dummy.c: Permission denied" → "cannot guess build type"。在 esac 前
        注入 HarmonyOS 分支（GUESS= 现代形态，E007/E160），使脚本直接输出
        aarch64-unknown-linux-ohos 并退出，完全不触碰临时目录。本地系统
        automake 1.16 的 config.guess（2023-08-22）已自带该分支，跳过。"""
        cg = os.path.join(self.source_folder, "config", "config.guess")
        if not os.path.isfile(cg):
            return
        with open(cg, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "HarmonyOS" in content:
            return
        arm = (
            "    *:HarmonyOS:*:*)\n"
            "\tcase \"$UNAME_MACHINE\" in\n"
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)          MACHINE=i686 ;;\n"
            "\t    *)             MACHINE=\"$UNAME_MACHINE\" ;;\n"
            "\tesac\n"
            "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
            "\t;;\n"
        )
        # 主 case 的 esac 紧跟 "# Do we have a guess based on uname results?"
        # 注释（该注释唯一），在其前插入分支；找不到再回退到 *:NetBSD:*:* 锚点。
        marker = "esac\n\n# Do we have a guess based on uname results?"
        if marker in content:
            content = content.replace(marker, arm + marker, 1)
        else:
            anchor = "    *:NetBSD:*:*)\n"
            if anchor not in content:
                raise ConanException(
                    "config.guess: neither esac marker nor NetBSD anchor found")
            content = content.replace(anchor, arm + anchor, 1)
        with open(cg, "w", encoding="utf-8") as f:
            f.write(content)

    def generate(self):
        # 把 tool_requires(automake/libtool) 的 bin 注入 conanbuild PATH，
        # 供 build() 里 bootstrap 的 aclocal/libtoolize/automake 解析
        # （centerim5/zzuf 同型先例）。
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # libusb header layout is <pkg>/include/libusb-1.0/libusb.h and
        # libg15.c/configure.in use #include <libusb-1.0/libusb.h> +
        # AC_CHECK_HEADERS/AC_CHECK_LIB, so -I/-L must point at the conan
        # libusb package (R33: no bare shell ${CC}/${CFLAGS}).
        if "libusb" in self.dependencies:
            dep = self.dependencies["libusb"]
            root = dep.package_folder
            include_dir = os.path.join(root, "include")
            lib_dir = os.path.join(root, "lib")
            tc.extra_cflags.append("-I" + include_dir)
            tc.extra_ldflags.append("-L" + lib_dir)
            # AC_CHECK_HEADERS runs only $CPP $CPPFLAGS (CFLAGS excluded), so
            # the -I must also reach CPPFLAGS.
            env = Environment()
            env.append("CPPFLAGS", "-I" + include_dir)
            envvars = env.vars(self)
            envvars.save_script("conancppflags")
        tc.generate()

    def build(self):
        # tarball 无预生成 configure：先跑 bootstrap 生成 configure 并应用
        # HMDFS umask 修复，再 configure/make。tool_requires 工具链经
        # conanbuild 环境注入（见 build_requirements/generate）。
        self._generate_configure()
        self._fix_configure_umask()
        self._fix_config_guess_ohos()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """OHOS XPM requires dlopen'd .so files to be code-signed."""
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                self.run('{oc} --remove-section .codesign "{p}" 2>/dev/null || true'
                         .format(oc=objcopy, p=path))
                self.run('{sg} sign -inFile "{p}" -outFile "{p}" -selfSign 1'
                         .format(sg=signer, p=path))
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = ["g15"]
        self.cpp_info.set_property("pkg_config_name", "libg15")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
