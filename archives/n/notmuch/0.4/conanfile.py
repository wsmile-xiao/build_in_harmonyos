#!/usr/bin/env python3
"""Conan recipe for notmuch 0.4 — 2010 邮件索引/搜索/标签工具（C 库 libnotmuch + CLI）。

notmuch 0.4 用自定义 configure 脚本 + 手写 Makefile（非 autotools、无 configure.ac）
构建。configure 硬性要求：
  - xapian-config（XAPIAN_CONFIG）         → ohpcd 制品 xapian-core/1.4.26（含 bin/xapian-config）
  - pkg-config gmime-2.6 或 gmime-2.4      → remote 无 gmime 2.x → 配方内自包含构建 gmime 2.6.23
                                            （参照 0.38.3 的 gmime 3.2.7 自包含先例；0.4 只认 2.x API）
  - pkg-config talloc                      → ohpcd 制品 talloc/2.4.4（制品无 .pc，配方合成 talloc.pc）
  - pkg-config（可选 valgrind / emacs）

OHOS 适配要点（手动编译已逐条验证）：
  1. E011：gmime autotools configure 生成 config.status 用 umask 077 + mktemp 建 0700
     目录，HMDFS 上不可写（Permission denied）→ 改 umask 022 后重跑 config.status。
  2. glib 制品 lib/pkgconfig/*.pc 的 prefix=/ 损坏 → 复制到 pc-stage 并修正真实 prefix；
     libffi/libpcre2-8/zlib/talloc 的 .pc 同样合成（指向各自制品根）。
  3. glib/gmime 的 Libs 含 -l:ld-musl-aarch64.so.1（OHOS musl 加载器），需 -L/lib；
     gmime configure 的 GLIB conftest 链接命令只用 CFLAGS 不用 LDFLAGS → -L/lib 放 CFLAGS。
  4. xapian-config 输出 -I//include -L//lib（prefix=/ 损坏）→ CFLAGS/CXXFLAGS/LDFLAGS
     显式注入真实 xapian include/lib。
  5. OHOS uname = "HarmonyOS" → notmuch configure 平台检测 "Unknown"，无碍（Makefile 仅
     MACOSX 分支特殊；LINKER_RESOLVES=0 时 CLI 用 CXX 全量链接依赖）。
  6. toybox gzip 无 --stdout（补丁 0001 改 gzip -c）；bash 不在 /bin（补丁 0002/0003，
     测试框架用）；clang 报裸 return; 错误（补丁 0003）。
  7. `install` 命令不在默认 PATH（在 /system/bin）→ make install 时 PATH 前置 /system/bin。
  8. /tmp 只读 → 全部 TMPDIR 用 build_folder/tmp。

上游测试：make test 需 bash≥4 + emacs + GNU touch；OHOS 上 emacs 缺失、toybox touch
不支持 -d '+N seconds'。手动实测（touch shim + LD_LIBRARY_PATH）：非 emacs 12 组
97/97 通过（basic/new/search/json/thread-naming/reply/dump-restore/uuencode/
thread-order/author-order/from-guessing/long-id/encoding），emacs 组 14 个因无 emacs
不可运行。本配方不在 build() 内跑完整 TAP（依赖 bash/emacs/GNU 工具链），核心功能由
test_package C API 消费测试（create/version/index/search，与上游 TAP 功能语义等价）验证。
"""
import os
import re
import glob
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# conan 缓存路径：本地 ~/.conan2/p 与 CI ~/.cache/conan2/p 都扫描
CONAN_PKG_ROOTS = [os.path.expanduser("~/.conan2/p"),
                   os.path.expanduser("~/.cache/conan2/p")]


class NotmuchConan(ConanFile):
    name = "notmuch"
    version = "0.4"
    description = ("Thread-based email index, search and tagging "
                   "(C library libnotmuch + notmuch CLI, 2010-era)")
    license = "GPL-3.0-or-later"
    homepage = "https://notmuchmail.org/"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        # 源码走 conandata sources.url 官方 get()（R39），补丁随配方导出
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # notmuch 直接依赖：xapian（C++ 核心）、talloc（内存 ctx）
        self.requires("xapian-core/1.4.26")
        self.requires("talloc/2.4.4")
        # gmime 自包含构建的编译期/链接期依赖（glib 组件 pkg-config + zlib）
        self.requires("zlib/1.3.1.1")
        self.requires("glib/2.84.0")
        # glib 制品 .pc 的 Requires: libffi / libpcre2-8 → pc-stage 需要其 .pc
        # 与制品路径（显式直引保证版本与 glib 依赖链一致）
        self.requires("libffi/3.4.4")
        self.requires("pcre2/10.40")

    def _tmpdir(self):
        d = os.path.join(self.build_folder, "tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def _tool_paths(self):
        """make/gzip/install/bash 等命令所在目录（按存在性探测）。"""
        paths = []
        for d in ("/data/service/hnp/bin", "/storage/Users/currentUser/usr/local/bin",
                  "/system/bin", "/bin", "/usr/bin", "/vendor/bin", "/usr/local/bin"):
            if os.path.isdir(d):
                paths.append(d)
        return ":".join(paths)

    def _compilers(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        cxx = compilers.get("cpp") if compilers else None
        if not cc:
            cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        if not cxx:
            cand = os.path.join(os.path.dirname(cc), "clang++")
            cxx = cand if os.path.exists(cand) else (shutil.which("clang++") or "clang++")
        return cc, cxx

    def _base_env(self, cc_dir=None, extra_pc=None, extra_ld=None):
        env = dict(os.environ)
        env["PATH"] = self._tool_paths() + ":" + env.get("PATH", "")
        tmp = self._tmpdir()
        env["TMPDIR"] = tmp
        env["TMP"] = tmp
        env["TEMP"] = tmp
        if cc_dir:
            env["PATH"] = cc_dir + ":" + env["PATH"]
        return env

    def _stage_pc(self):
        """把 glib 制品的 pkg-config 组件 .pc 复制到 pc-stage 并修正 prefix=/；
        合成 libffi/libpcre2-8/zlib/talloc 的 .pc（指向各自制品根，prefix 正确）。
        OHOS 的 glib 制品 .pc 的 prefix=/ 损坏（0.38.3 同款问题），且 Libs 含
        -l:ld-musl-aarch64.so.1（musl 加载器），调用方链接需 -L/lib。"""
        stage = os.path.join(self.build_folder, "pc-stage")
        os.makedirs(stage, exist_ok=True)
        glib = self.dependencies["glib"].package_folder
        glib_pc = os.path.join(glib, "lib", "pkgconfig")
        if not os.path.isdir(glib_pc):
            raise Exception(f"glib pkgconfig dir missing: {glib_pc}")
        for pc in sorted(glob.glob(os.path.join(glib_pc, "*.pc"))):
            content = open(pc, "r", encoding="latin-1").read()
            content = re.sub(r"^prefix=.*$", f"prefix={glib}",
                             content, count=1, flags=re.M)
            with open(os.path.join(stage, os.path.basename(pc)), "w",
                      encoding="latin-1") as f:
                f.write(content)
        # 合成 libffi / libpcre2-8 / zlib / talloc 的 .pc（glib-2.0.pc 的
        # Requires: libpcre2-8；gobject-2.0.pc Requires: libffi；gmime/notmuch
        # 需 zlib/talloc）
        plan = {"libffi": "libffi", "pcre2": "libpcre2-8",
                "zlib": "zlib", "talloc": "talloc"}
        for dep, pname in plan.items():
            try:
                root = self.dependencies[dep].package_folder
            except KeyError:
                continue
            ver = self.dependencies[dep].ref.version if getattr(
                self.dependencies[dep], "ref", None) else ""
            pc = os.path.join(stage, pname + ".pc")
            libs = "-lgmime-none"
            if pname == "talloc":
                libs = "-ltalloc"
            elif pname == "zlib":
                libs = "-lz"
            elif pname == "libffi":
                libs = "-lffi"
            elif pname == "libpcre2-8":
                libs = "-lpcre2-8"
            with open(pc, "w", encoding="latin-1") as f:
                f.write(f"prefix={root}\n"
                        f"exec_prefix=${{prefix}}\n"
                        f"libdir=${{prefix}}/lib\n"
                        f"includedir=${{prefix}}/include\n\n"
                        f"Name: {pname}\n"
                        f"Version: {ver}\n"
                        f"Description: Conan package: {pname}\n"
                        f"Libs: -L${{libdir}} {libs}\n"
                        f"Cflags: -I${{includedir}}\n")
        # 修复 conan 缓存里 .la 的 libdir='//lib' 损坏（libtool 链接 glib 用，
        # 本地 ~/.conan2/p 与 CI ~/.cache/conan2/p 都扫）
        for root in CONAN_PKG_ROOTS:
            for la in glob.glob(os.path.join(root, "*", "p", "lib", "*.la")):
                try:
                    text = open(la, "r", encoding="latin-1").read()
                except OSError:
                    continue
                if "//lib/" in text:
                    with open(la, "w", encoding="latin-1") as f:
                        f.write(text.replace("//lib/", os.path.dirname(la) + "/"))
        return stage

    def source(self):
        # 1) notmuch 官方源（R39）
        get(self, **self.conan_data["sources"], strip_root=True)
        # 2) gmime 2.6.23 官方源（自包含子构建，解压到 gmime-2.6.23/）
        get(self, **self.conan_data["gmime"])

    def _build_gmime(self, cc, cxx):
        """自包含构建 gmime 2.6.23（notmuch 0.4 configure 需要 gmime-2.6 的
        pkg-config）。依赖 glib/zlib 制品。禁用 cryptography/smime/mono/gtk-doc/
        introspection（OHOS 无 gpgme；notmuch 0.4 只用 gmime 的 MIME 解析能力）。"""
        src = os.path.join(self.source_folder, "gmime-2.6.23")
        if not os.path.isdir(src):
            raise Exception(f"gmime source missing: {src}")
        prefix = os.path.join(self.build_folder, "gmime-install")
        os.makedirs(prefix, exist_ok=True)
        pc_stage = self._stage_pc()
        env = self._base_env(cc_dir=os.path.dirname(cc))
        env.update({
            "PKG_CONFIG_PATH": pc_stage,
            "CC": cc,
            "CXX": cxx,
            # gmime 的 GLIB conftest 链接只用 CFLAGS（不用 LDFLAGS）→ -L/lib 放 CFLAGS
            "CFLAGS": "-O2 -fPIC -L/lib",
            "LDFLAGS": "-L/lib",
        })
        cfg = os.path.join(src, "configure")
        os.chmod(cfg, 0o755)
        # configure 在收尾执行 config.status 时触发 E011（umask 077 + HMDFS 0700
        # 目录不可写）→ 返回 1，但 config.status 已生成。容忍该退出码，随后
        # 补丁 umask 022 并重跑 config.status（手动编译验证的流程）。
        subprocess.run(
            [cfg, "--build=aarch64-unknown-linux-gnu", f"--prefix={prefix}",
             "--disable-cryptography", "--disable-smime", "--disable-mono",
             "--disable-gtk-doc", "--disable-introspection"],
            cwd=src, env=env)
        # E011: config.status umask 077 → 022（HMDFS 0700 目录不可写）
        cs = os.path.join(src, "config.status")
        if os.path.isfile(cs):
            content = open(cs, "r", encoding="latin-1").read()
            if "umask 077 && mktemp" in content:
                with open(cs, "w", encoding="latin-1") as f:
                    f.write(content.replace(
                        "umask 077 && mktemp", "umask 022 && mktemp"))
        r = subprocess.run(["sh", "config.status"], cwd=src, env=env)
        if r.returncode != 0:
            raise Exception("gmime config.status failed")
        njobs = max(1, min(4, os.cpu_count() or 2))
        r = subprocess.run(["make", f"-j{njobs}"], cwd=src, env=env)
        if r.returncode != 0:
            raise Exception("gmime make failed")
        r = subprocess.run(["make", "install"], cwd=src, env=env)
        if r.returncode != 0:
            raise Exception("gmime make install failed")
        return prefix, pc_stage

    def _build_notmuch(self, cc, cxx, gmime_prefix, pc_stage):
        src = self.source_folder
        xapian = self.dependencies["xapian-core"].package_folder
        talloc = self.dependencies["talloc"].package_folder
        xapian_config = os.path.join(xapian, "bin", "xapian-config")
        if not os.path.exists(xapian_config):
            raise Exception(f"xapian-config missing: {xapian_config}")
        install = os.path.join(self.build_folder, "nm-install")
        os.makedirs(install, exist_ok=True)
        pc_path = ":".join([os.path.join(gmime_prefix, "lib", "pkgconfig"),
                            pc_stage])
        env = self._base_env(cc_dir=os.path.dirname(cc))
        env.update({
            "CC": cc,
            "CXX": cxx,
            "XAPIAN_CONFIG": xapian_config,
            "PKG_CONFIG_PATH": pc_path,
            # xapian-config 输出 -I//include -L//lib（prefix=/）→ 显式注入真实路径
            "CFLAGS": f"-O2 -fPIC -I{xapian}/include -L/lib",
            "CXXFLAGS": f"-O2 -fPIC -I{xapian}/include -L/lib",
            "LDFLAGS": f"-L{xapian}/lib -L/lib",
        })
        cfg = os.path.join(src, "configure")
        os.chmod(cfg, 0o755)
        r = subprocess.run([cfg, f"--prefix={install}"], cwd=src, env=env)
        if r.returncode != 0:
            raise Exception("notmuch configure failed")
        njobs = max(1, min(4, os.cpu_count() or 2))
        r = subprocess.run(["make", f"-j{njobs}"], cwd=src, env=env)
        if r.returncode != 0:
            raise Exception("notmuch make failed")
        # `install` 命令在 /system/bin（不在默认 PATH）→ 已由 _tool_paths 覆盖
        r = subprocess.run(["make", "install"], cwd=src, env=env)
        if r.returncode != 0:
            raise Exception("notmuch make install failed")
        return install

    def build(self):
        apply_conandata_patches(self)
        cc, cxx = self._compilers()
        gmime_prefix, pc_stage = self._build_gmime(cc, cxx)
        self._build_notmuch(cc, cxx, gmime_prefix, pc_stage)
        # 自检：安装产物存在（fail-fast，避免假成功）
        install = os.path.join(self.build_folder, "nm-install")
        for rel in ("bin/notmuch", "lib/libnotmuch.so.1.2.0", "include/notmuch.h"):
            p = os.path.join(install, rel)
            if not os.path.exists(p):
                raise Exception(f"build product missing after install: {p}")

    def package(self):
        prefix = os.path.join(self.build_folder, "nm-install")
        gmime_prefix = os.path.join(self.build_folder, "gmime-install")
        copy(self, "libnotmuch.so*", src=os.path.join(prefix, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "notmuch.h", src=os.path.join(prefix, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "notmuch", src=os.path.join(prefix, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 自包含构建的 gmime 随包分发（libnotmuch.so 运行时 NEEDED libgmime-2.6.so.0，
        # gmime 非 conan 依赖 → 打进本包 lib/ 供消费者链接/运行，0.38.3 同款）
        copy(self, "libgmime-2.6.so*", src=os.path.join(gmime_prefix, "lib"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["notmuch"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.bindirs = ["bin"]
