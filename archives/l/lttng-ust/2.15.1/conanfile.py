#!/usr/bin/env python3
"""Conan recipe — lttng-ust 2.15.1 (autotools, C).

LTTng userspace tracing library (lttng.org). Produces liblttng-ust* shared
libraries + lttng-gen-tp tool.

OHOS adaptation notes:
- Dep: liburcu/0.15.6 (ohpcd) — configure PKG_CHECK_MODULES(URCU liburcu>=0.15).
- autotools OHOS platform: config.guess/config.sub inline patch (scamp/cif-api
  pattern) + explicit --host=aarch64-unknown-linux-ohos.
- OHOS umask 077 (E011): configure/config.status tmp dir 700 perms on hmdfs
  -> patch umask + mkdir -p -m 755 (cloog/dfu pattern).
- Runtime: tracer/tracepoint needs kernel/usrland support — declared per rule 1.2.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LttngUstConan(ConanFile):
    name = "lttng-ust"
    version = "2.15.1"
    description = "LTTng userspace tracing library"
    license = "LGPL-2.1-or-later"
    homepage = "https://lttng.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # lttng-ust 硬性要求共享库（configure: "LTTng-UST requires shared libraries
    # to be enabled"）——默认 shared=True
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # liburcu（UST 核心依赖，RCU 库）
        self.requires("liburcu/0.15.6", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_tracepoint_dlclose()

    def _patch_tracepoint_dlclose(self):
        """lttng_ust__tracepoints__destroy()（destructor 清理）对 liblttngust_handle
        调 dlclose——OHOS musl 的 dlclose 对该 handle 返回 -1，上游代码
        `if (ret) { fprintf("Error in dlclose"); abort(); }` 直接 abort（Signal 6）。
        destructor 阶段清理失败不影响功能 → patch 为仅警告不 abort。"""
        hdr = os.path.join(self.source_folder, "include", "lttng", "tracepoint.h")
        if not os.path.isfile(hdr):
            self.output.warning("tracepoint.h not found; dlclose patch skipped")
            return
        text = open(hdr, encoding="utf-8", errors="ignore").read()
        old = ('\t\tfprintf(stderr, "Error (%d) in dlclose\\n", ret);\n'
               '\t\tabort();')
        old3 = ('\t\t\tfprintf(stderr, "Error (%d) in dlclose\\n", ret);\n'
                '\t\t\tabort();')
        new = ('\t\tfprintf(stderr, "Warning: dlclose failed (%d) on OHOS\\n", ret);')
        new3 = ('\t\t\tfprintf(stderr, "Warning: dlclose failed (%d) on OHOS\\n", ret);')
        n = text.count(old) + text.count(old3)
        if n > 0:
            text = text.replace(old, new).replace(old3, new3)
            open(hdr, "w", encoding="utf-8").write(text)
            self.output.info(f"patched tracepoint.h: {n} dlclose failure blocks -> warning (no abort, OHOS musl dlclose returns -1)")
        else:
            self.output.info("tracepoint.h dlclose block not matched; skip")

    def generate(self):
        # liburcu 的 .pc（PKG_CHECK_MODULES(URCU liburcu) 命中）
        PkgConfigDeps(self).generate()
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # numa 集成可选（configure 的 arm* 自动禁用判断不匹配 aarch64，
        # 不 --disable-numa 会报 "libnuma is not available"）——numa 对核心
        # tracing 非必需，显式禁用
        tc.configure_args.append("--disable-numa")
        # 注入依赖 include/lib 兜底（extra_cflags 必须在 tc.generate() 前设置）
        # OHOS/musl：libpthread 合并进 libc，lld --no-allow-shlib-undefined 严格检查
        # 误报 pthread_setcancelstate 未定义 → 允许共享库未定义符号
        tc.extra_ldflags.append("-Wl,--allow-shlib-undefined")
        for _n, dep in self.dependencies.items():
            for p in dep.cpp_info.includedirs:
                tc.extra_cflags.append("-I" + p)
            for p in dep.cpp_info.libdirs:
                tc.extra_ldflags.append("-L" + p)
        tc.generate()
        # autoconf $ac_tmp 落 /tmp（OHOS 只读）→ build_folder（cloog/dfu 同款）
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        envvars = env.vars(self)
        envvars.save_script("conantmpdir")

    def build(self):
        apply_conandata_patches(self)
        self._patch_ohos_platform()
        # 清理前次失败残留的 conf* 临时目录（umask 077 建 700 权限写不进）
        for stale in glob.glob(os.path.join(self.build_folder, "conf*")):
            if os.path.isdir(stale):
                shutil.rmtree(stale, ignore_errors=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])

    def _patch_ohos_platform(self):
        """config.guess/config.sub OHOS 识别 + configure umask 077 修复（E011）。
        lttng-ust 的 config.guess/config.sub 在 config/ 子目录且为**旧版格式**
        （config.sub kernel-os 组合 1775 行 `linux-gnu*` 无 `-` 结尾、config.guess
        aarch64 用 GUESS= 变量）——旧版格式 patch（与 util-linux 新版相反）。"""
        import os as _os
        cfg = _os.path.join(self.source_folder, "configure")
        if _os.path.isfile(cfg):
            ctext = open(cfg, encoding="utf-8", errors="ignore").read()
            if "umask 000" not in ctext:
                nl = ctext.find("\n")
                ctext = ctext[:nl+1] + "umask 000\n" + ctext[nl+1:]
                changed = True
            else:
                changed = False
            old_mkt = '(umask 077 && mktemp -d "./confXXXXXX")'
            if old_mkt in ctext:
                ctext = ctext.replace(old_mkt, '(umask 000 && mktemp -d "./confXXXXXX")')
                changed = True
            if changed:
                with open(cfg, "w") as f:
                    f.write(ctext)
                self.output.info("patched configure: umask 077->000 (E011 hmdfs tmp dir)")
        # lttng-ust 的 config.guess/config.sub 在 config/ 子目录（旧版格式）
        for name in ("config.guess", "config.sub"):
            for base in (self.source_folder, os.path.join(self.source_folder, "config"),
                         os.path.join(self.source_folder, "build-aux")):
                path = os.path.join(base, name)
                if not os.path.isfile(path):
                    continue
                text = open(path, encoding="utf-8", errors="ignore").read()
                changed = False
                if name == "config.sub":
                    # os 合法性列表加 ohos（旧版：zephyr*) 单行结尾 / 新版：zephyr* \ 续行）
                    old1a = "| nsk* | powerunix* | genode* | zvmoe* | qnx* | emx* | zephyr*)"
                    old1b = "| nsk* | powerunix* | genode* | zvmoe* | qnx* | emx* | zephyr* \\"
                    if old1a in text and "ohos*)" not in text:
                        text = text.replace(old1a, old1a.replace("zephyr*)", "zephyr* | ohos*)"), 1)
                        changed = True
                    elif old1b in text and "ohos*)" not in text:
                        text = text.replace(old1b, old1b + "\n\t     | ohos* \\", 1)
                        changed = True
                    # kernel-os 组合加 linux-ohos（旧版：linux-gnu* 无 - 结尾）
                    # 注意：插入行必须带 `\` 续行符，否则破坏 case 语句语法
                    old2 = "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\"
                    if old2 in text and "linux-ohos*" not in text:
                        text = text.replace(old2, old2.replace("linux-newlib* \\", "linux-newlib* | linux-ohos* \\"), 1)
                        changed = True
                else:  # config.guess — 旧版 GUESS= 变量格式
                    old3 = "    aarch64:Linux:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n\t;;"
                    if old3 in text and "OHOS" not in text:
                        new3 = ("    aarch64:Linux:*:*)\n"
                                "\tcase `uname` in\n"
                                "\t  *OHOS*) echo $UNAME_MACHINE-unknown-linux-ohos ; exit ;;\n"
                                "\tesac\n"
                                "\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n\t;;")
                        text = text.replace(old3, new3, 1)
                        changed = True
                if changed:
                    with open(path, "w") as f:
                        f.write(text)
                    self.output.info(f"patched {base}/{name}: OHOS platform recognition")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSES", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["lttng-ust", "lttng-ust-tracepoint", "lttng-ust-provider"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["liburcu::liburcu"]
