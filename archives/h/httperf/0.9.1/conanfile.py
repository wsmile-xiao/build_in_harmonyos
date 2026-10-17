#!/usr/bin/env python3
"""Conan recipe — httperf 0.9.1 (Autotools)"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HttperfConan(ConanFile):
    name = "httperf"
    version = "0.9.1"
    description = "httperf - HTTP load generator (0.9.1)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/httperf/httperf"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # GitHub tarball ships only configure.ac (no generated configure),
        # so autoreconf --install is required. configure.ac uses both
        # AM_INIT_AUTOMAKE (→ automake) and AC_PROG_LIBTOOL (→ libtool),
        # and automake pulls m4 transitively. HNP on CI workers provides
        # autoconf + m4 but NOT automake/libtool, so pull those via
        # tool_requires from ohpcd (built for aarch64-ohos).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub tarball ships only configure.ac (no generated configure),
        # so autoreconf is required before configure.
        autotools.autoreconf()
        # E007: config.guess/config.sub 由 autoreconf 生成, 不含 HarmonyOS 检测,
        # 导致 configure 报 "cannot guess build type". 这里内联 patch 加 OHOS 分支.
        self._patch_config_guess_sub()
        # E011: HMDFS maps owner UID, so `umask 077` temp dirs (confXXXXXX)
        # created by config.status become unwritable. Relax to 022.
        self.run(
            "sed -i 's/umask 077/umask 022/g' configure",
            cwd=self.source_folder,
        )
        autotools.configure()
        autotools.make(args=["-j1"])

    def _patch_config_guess_sub(self):
        """E007: autoreconf 生成的 config.guess/sub 不识别 HarmonyOS, 内联补丁.

        对应 scripts/patch-autotools-ohos.pl 的 5 项检查:
          config.guess: __OHOS__ LIBC 分支 + HarmonyOS case 块
          config.sub:  ohos-linux triplet + ohos* OS 类型 + linux-ohos kernel
        """
        import os
        cg = os.path.join(self.source_folder, "config.guess")
        cs = os.path.join(self.source_folder, "config.sub")
        if not (os.path.isfile(cg) and os.path.isfile(cs)):
            return  # autoreconf 可能没生成, 跳过让 configure 报错

        def read(p):
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        def write(p, c):
            with open(p, "w", encoding="utf-8") as f:
                f.write(c)

        # ── config.guess ──
        gc = read(cg)
        changed = False
        if "__OHOS__" not in gc:
            # 在 __ANDROID__/LIBC=android 之后插入 __OHOS__ LIBC 检测
            import re
            gc2 = re.sub(
                r"(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                gc, count=1, flags=re.MULTILINE,
            )
            if gc2 != gc:
                gc = gc2
                changed = True
        if "HarmonyOS" not in gc:
            # 在 NetBSD case 之前插入 HarmonyOS 识别块
            block = (
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n"
            )
            import re
            gc2 = re.sub(
                r"(^[ \t]+\*\:NetBSD\:\*\:\*\)[ \t]*\n)",
                lambda m: block + m.group(1),
                gc, count=1, flags=re.MULTILINE,
            )
            if gc2 != gc:
                gc = gc2
                changed = True
        if changed:
            write(cg, gc)

        # ── config.sub ──
        sc = read(cs)
        changed = False
        if "ohos-linux" not in sc:
            # 在 android-linux 块之后插入 ohos-linux triplet
            import re
            sc2 = re.sub(
                r"^(\s*android-linux\)\s*\n)((\s*)basic_machine=\$field1-unknown\s*\n)((\s*)basic_os=linux-android\s*\n)(\s*;;\s*\n)",
                r"\1\2\4\6\tohos-linux)\n\3basic_machine=$field1-unknown\n\5basic_os=linux-ohos\n\6",
                sc, count=1, flags=re.MULTILINE,
            )
            if sc2 != sc:
                sc = sc2
                changed = True
        if "ohos*" not in sc:
            import re
            sc2 = re.sub(
                r"(gnu\*\s*\|\s*android\*)",
                r"\1 | ohos*",
                sc, count=1,
            )
            if sc2 != sc:
                sc = sc2
                changed = True
        if "linux-ohos" not in sc:
            import re
            sc2 = re.sub(
                r"(linux-uclibc\*[/-]?\s*)\)",
                r"\1| linux-ohos*)",
                sc, count=1,
            )
            if sc2 != sc:
                sc = sc2
                changed = True
        if changed:
            write(cs, sc)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Application package: executable only, no libraries to link
        self.cpp_info.bindirs = ["bin"]
