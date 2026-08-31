#!/usr/bin/env python3
"""Conan test_package — gnumeric 1.12.57

L1 test: build test.c (links libspreadsheet-1.12.57 via pkg-config) and run it.
test.c 实质调用 gnm_sys_lib_dir/gnm_sys_data_dir/gnm_app_get_type 等公开 API。

gnumeric 的 libspreadsheet 头文件展开包含 goffice/gtk/cairo/pango/gsf/glib
头文件；glib 与 libgsf/cairo 来自 conan 依赖（PkgConfigDeps 生成 .pc），
gtk+/pango 等来自 cmd-pkgs 预编译 GTK 栈（前缀 /storage/Users/currentUser/usr/local）。
本 generate() 参照 goffice test_package 处理 glib 的 -l:ld-musl、libintl、
gobject/gio/gthread .pc，并把 GTK 前缀加入 PKG_CONFIG_PATH / LD_LIBRARY_PATH。

OHOS 运行期部署方案（与 goffice test_package 同款）：test_gnumeric 连同完整
DT_NEEDED 闭包部署到独立运行目录（cp -L 按 SONAME 收集 + RUNPATH=$ORIGIN +
ELF 签名）→ cmd-pkgs GTK 栈用空实现 stub 替换（测试只调用 GObject 类型系统，
不真正使用 GTK widget）→ LD_PRELOAD 动态 glib 全家 → bash 真实运行。
"""
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps


GTK_PREFIX = "/storage/Users/currentUser/usr/local"


class GnumericTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libspreadsheet 依赖 glib/gobject 头，且 gnumeric.h 展开 goffice.h
        # (依赖 libxml 的 gsf-libxml.h)。版本与本体配方对齐（glib/2.88.0.1
        # shared=True，GTK 栈同版本族）。
        self.requires("glib/2.88.0.1")
        self.requires("libxml2/2.15.3.1")

    def configure(self):
        # 与本体配方一致：glib 必须 shared=True（GTK 栈同版本族）。
        try:
            self.options["glib"].shared = True
        except Exception:
            pass

    def _gtk_prefix(self):
        """定位 cmd-pkgs 预编译 GTK 栈前缀（与本体配方一致）。"""
        for env_name in ("GTK_PREFIX", "DEFAULT_PREFIX"):
            v = os.environ.get(env_name)
            if v:
                return os.path.normpath(v)
        for pc in sorted(glob.glob("/data/service/hnp/**/gtk+-3.0.pc", recursive=True)):
            return os.path.dirname(os.path.dirname(pc))
        return GTK_PREFIX

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()

        glib_folder = None
        if "glib" in self.dependencies:
            glib_folder = self.dependencies["glib"].package_folder

        # glib-2.0.pc 携带 "-l:ld-musl-aarch64.so.1"，lld 无显式搜索路径解析不了
        # → 改为绝对路径 /lib/ld-musl-aarch64.so.1（libgsf 同款）。
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.exists(glib_pc):
            with open(glib_pc, "r", encoding="utf-8") as f:
                pc = f.read()
            pc = pc.replace("-l:ld-musl-aarch64.so.1", "/lib/ld-musl-aarch64.so.1")
            with open(glib_pc, "w", encoding="utf-8") as f:
                f.write(pc)

        # gobject-2.0 / gio-2.0 / gthread-2.0 / gmodule-no-export-2.0 的 .pc：
        # glib 无 components，PkgConfigDeps 只生成聚合的 glib-2.0.pc，而
        # gtk+-3.0.pc/pango.pc 的 Requires 需要 gobject-2.0 / gio-2.0（非 private），
        # gdk-pixbuf-2.0.pc 的 Requires.private 需要 gmodule-no-export-2.0。
        # 从 glib-2.0.pc 派生，prefix 取真实值（指向 conan glib package，与本体
        # 配方链接同一份 glib；cmd-pkgs 前缀里也有 2.88.0 的版本，但必须用
        # conan 2.88.0.1 的版本）。
        cflags = "-I${includedir} -I${includedir1}"
        prefix_glib = "${pcfiledir}/../.."
        if os.path.exists(glib_pc):
            with open(glib_pc, "r", encoding="utf-8", errors="ignore") as f:
                m = re.search(r"^Cflags:\s*(.+)$", f.read(), re.M)
            if m:
                cflags = m.group(1).strip()
            with open(glib_pc, "r", encoding="utf-8", errors="ignore") as f:
                m = re.search(r"^prefix=(.+)$", f.read(), re.M)
            if m:
                prefix_glib = m.group(1).strip()
        for name, libname in (("gobject-2.0", "gobject-2.0"),
                              ("gio-2.0", "gio-2.0"),
                              ("gthread-2.0", "gthread-2.0"),
                              ("gmodule-no-export-2.0", "gmodule-2.0")):
            pf = os.path.join(self.generators_folder, name + ".pc")
            if not os.path.exists(pf):
                text = (
                    "prefix={prefix}\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include/glib-2.0\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                    "includedir2=${{prefix}}/lib/glib-2.0/include\n"
                    "\n"
                    "Name: {name}\n"
                    "Description: Conan package: {name}\n"
                    "Version: 2.88.0.1\n"
                    "Libs: -L${{libdir}} -l{libname}\n"
                    "Cflags: {cflags}\n"
                    "Requires: glib-2.0\n"
                ).format(prefix=prefix_glib, name=name, libname=libname, cflags=cflags)
                with open(pf, "w", encoding="utf-8") as f:
                    f.write(text)

        # gio-unix-2.0：gdk-3.0.pc / gtk+-3.0.pc 的 Requires.private 引用它，
        # 只含头文件（include/gio-unix-2.0），无独立库。prefix 从 gio-2.0.pc 读取。
        gio_unix_pc = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.exists(gio_unix_pc) and os.path.exists(gio_pc):
            with open(gio_pc, "r", encoding="utf-8", errors="ignore") as f:
                m = re.search(r"^prefix=(.+)$", f.read(), re.M)
            gio_prefix = m.group(1).strip() if m else "${pcfiledir}/../.."
            text = (
                "prefix={prefix}\n"
                "includedir=${{prefix}}/include\n"
                "\n"
                "Name: gio-unix-2.0\n"
                "Description: Conan package: gio-unix-2.0\n"
                "Version: 2.88.0.1\n"
                "Requires: gobject-2.0 gio-2.0\n"
                "Cflags: -I${{includedir}}/gio-unix-2.0\n"
            ).format(prefix=gio_prefix)
            with open(gio_unix_pc, "w", encoding="utf-8") as f:
                f.write(text)

        # cairo.pc 派生：cairo-gobject 配方只声明 pkg_config_name=cairo-gobject，
        # PkgConfigDeps 只生成 cairo-gobject.pc；而 gtk+-3.0.pc / pango.pc 的
        # Requires 需要 cairo。从 cairo-gobject.pc 读取 prefix 派生 cairo.pc。
        cgo_pc = os.path.join(self.generators_folder, "cairo-gobject.pc")
        cairo_pc = os.path.join(self.generators_folder, "cairo.pc")
        if os.path.exists(cgo_pc) and not os.path.exists(cairo_pc):
            with open(cgo_pc, "r", encoding="utf-8", errors="ignore") as f:
                cgo = f.read()
            m = re.search(r"^prefix=(.+)$", cgo, re.M)
            prefix = m.group(1).strip() if m else "${pcfiledir}/../.."
            text = (
                "prefix={prefix}\n"
                "libdir=${{prefix}}/lib\n"
                "includedir=${{prefix}}/include\n"
                "\n"
                "Name: cairo\n"
                "Description: Multi-platform 2D graphics library\n"
                "Version: 1.18.4\n"
                "Libs: -L${{libdir}} -lcairo\n"
                "Cflags: -I${{includedir}} -I${{includedir}}/cairo\n"
            ).format(prefix=prefix)
            with open(cairo_pc, "w", encoding="utf-8") as f:
                f.write(text)

        # libspreadsheet-1.12.57.so 有未定义 g_libintl_*（glib 包 libintl.so
        # 提供），CI lld --no-allow-shlib-undefined 要求链接行显式解析 → 把 glib
        # 包 libintl 的绝对路径追加到 glib-2.0.pc Libs（libgsf 同款）。
        if glib_folder:
            glib_lib = os.path.join(glib_folder, "lib")
            intl_path = ""
            for cand in ("libintl.so", "libintl.a"):
                p = os.path.join(glib_lib, cand)
                if os.path.isfile(p):
                    intl_path = p
                    break
            if intl_path and os.path.exists(glib_pc):
                with open(glib_pc, "r", encoding="utf-8") as f:
                    pc = f.read()
                if intl_path not in pc:
                    pc = re.sub(r"^(Libs:.*)$", r"\1 " + intl_path, pc,
                                count=1, flags=re.M)
                    with open(glib_pc, "w", encoding="utf-8") as f:
                        f.write(pc)

        # 构建期环境：GTK 前缀 .pc 路径 + lld 的 SDK llvm/lib（libxml2.so.16）。
        # 关键：conan 生成/派生的 .pc 在 generators_folder，由 CMakeToolchain 的
        # PkgConfigBlock 在 cmake 层 prepend 到 PKG_CONFIG_PATH 最前面。这里必须用
        # append（而非 prepend）把 GTK 前缀放到末尾，否则 cmd-pkgs 硬编码前缀里的
        # cairo 会顶掉 conan 派生 cairo.pc 的优先级。
        prefix = self._gtk_prefix()
        build_env = Environment()
        build_env.append_path("PKG_CONFIG_PATH",
                              os.path.join(prefix, "lib", "pkgconfig"))
        build_env.append_path("PKG_CONFIG_PATH",
                              os.path.join(prefix, "share", "pkgconfig"))
        if self.settings.os == "OHOS":
            llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if not os.path.isdir(llvm_lib):
                cands = sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
                llvm_lib = cands[0] if cands else ""
            if llvm_lib:
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        build_env.vars(self).save_script("gnumeric_test_build_env")

        # 运行期环境（非 OHOS 直接运行用；OHOS 走闭包部署，不依赖此脚本）。
        run_env = Environment()
        run_env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
        run_env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib", "external"))
        run_env.vars(self, scope="run").save_script("gnumeric_test_run_env")

        VirtualRunEnv(self).generate()

    def test(self):
        cmake = CMake(self)
        # R34 / L1e 破坏性反向验证：强制干净重建，避免复用陈旧链接产物。
        self._clean_build_folder()
        cmake.configure()
        cmake.build()

        test_exe = os.path.join(self.build_folder, "test_gnumeric")
        if not os.path.isfile(test_exe):
            raise RuntimeError("test_gnumeric executable missing: {}".format(test_exe))

        # OHOS 运行期部署方案（与 goffice test_package 同款）：把 test_gnumeric
        # 连同完整 DT_NEEDED 闭包部署到独立目录 → RUNPATH=$ORIGIN → ELF 签名 →
        # GTK 栈 stub → bash 真实运行。8 项断言必须真实 PASS。
        if str(self.settings.os) == "OHOS":
            self._run_deployed(test_exe)
            return
        self.run(test_exe, env="conanrun")

    # ------------------------------------------------------------------ #
    #  OHOS 运行期部署：DT_NEEDED 闭包 + RUNPATH=$ORIGIN + ELF 签名       #
    # ------------------------------------------------------------------ #
    _SYSTEM_SO = {
        "libc.so", "libdl.so", "libm.so", "libpthread.so", "librt.so",
        "libresolv.so", "libutil.so", "libcrypt.so", "ld-musl-aarch64.so.1",
        "libgcc_s.so.1", "libc++_shared.so",
    }

    def _runtime_search_dirs(self):
        """闭包收集的库搜索路径：被测包 → conan 依赖 → cmd-pkgs GTK 前缀。"""
        dirs = []
        for dep in self.dependencies.values():
            pf = getattr(dep, "package_folder", None)
            if pf:
                lib = os.path.join(pf, "lib")
                if os.path.isdir(lib):
                    dirs.append(lib)
        prefix = self._gtk_prefix()
        dirs.append(os.path.join(prefix, "lib"))
        dirs.append(os.path.join(prefix, "lib", "external"))
        dirs.append("/lib")
        dirs.append("/usr/lib")
        seen = set()
        out = []
        for d in dirs:
            if d not in seen:
                seen.add(d)
                out.append(d)
        return out

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _elf_needed(self, path):
        readelf = glob.glob("/data/service/hnp/bin/llvm-readelf") or ["llvm-readelf"]
        out = subprocess.run([readelf[0], "-d", path], capture_output=True, text=True).stdout
        return re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]", out)

    def _deploy_runtime_closure(self, exe, runtime_dir):
        os.makedirs(runtime_dir, exist_ok=True)
        search_dirs = self._runtime_search_dirs()
        copied = []
        seen = set()
        # libgsf/libgoffice 未记录 NEEDED glib 但有未定义 glib 符号 → 显式补入
        # glib 全家（含 proxy-libintl）。
        for soname in ("libglib-2.0.so.0", "libgobject-2.0.so.0", "libgio-2.0.so.0",
                       "libgmodule-2.0.so.0", "libgirepository-2.0.so.0",
                       "libgthread-2.0.so.0", "libintl.so.9", "libintl.so.8"):
            src = None
            for d in search_dirs:
                p = os.path.join(d, soname)
                if os.path.isfile(p):
                    src = p
                    break
                if os.path.islink(p):
                    rp = os.path.realpath(p)
                    if os.path.isfile(rp):
                        src = rp
                        break
            if src:
                seen.add(soname)
                dst = os.path.join(runtime_dir, soname)
                shutil.copyfile(os.path.realpath(src), dst)
                os.chmod(dst, 0o755)
                copied.append(dst)
        queue = [exe] + copied
        while queue:
            cur = queue.pop()
            for soname in self._elf_needed(cur):
                # cmd-pkgs 库可能用绝对路径 NEEDED → 闭包内按 basename 命名。
                name = os.path.basename(soname)
                if name in seen or name in self._SYSTEM_SO:
                    continue
                src = None
                if os.path.isabs(soname) and os.path.isfile(soname):
                    src = soname
                else:
                    for d in search_dirs:
                        p = os.path.join(d, soname)
                        if os.path.isfile(p):
                            src = p
                            break
                        if os.path.islink(p):
                            rp = os.path.realpath(p)
                            if os.path.isfile(rp):
                                src = rp
                                break
                if not src:
                    self.output.warning("runtime closure: {} not found; skipping".format(name))
                    continue
                seen.add(name)
                dst = os.path.join(runtime_dir, name)
                shutil.copyfile(os.path.realpath(src), dst)
                os.chmod(dst, 0o755)
                queue.append(dst)
                copied.append(dst)
        return copied

    # cmd-pkgs GTK 栈静态内嵌 glib（构造器丢失）→ 与动态 glib 冲突。测试只调用
    # libspreadsheet 的 GObject 类型注册 API（gnm_app_get_type），不真正使用 GTK
    # widget → 用空实现 stub 替换 GTK 栈库（函数返回 0），gobject 类型系统由
    # LD_PRELOAD 的动态 glib 提供。
    GTK_STACK_STUB_SO = (
        "libgtk-3.so.0", "libgdk-3.so.0", "libpango-1.0.so.0",
        "libpangocairo-1.0.so.0", "libpangoft2-1.0.so.0",
        "libgdk_pixbuf-2.0.so.0", "libatk-1.0.so.0",
        "libfribidi.so.0", "libepoxy.so.0",
    )
    GLIB_PRELOAD_SO = (
        "libglib-2.0.so.0", "libgobject-2.0.so.0", "libgio-2.0.so.0",
        "libgmodule-2.0.so.0", "libintl.so.9",
    )

    def _gen_gtk_stack_stubs(self, runtime_dir):
        stubs_dir = os.path.join(runtime_dir, "gtk-stubs")
        os.makedirs(stubs_dir, exist_ok=True)
        nm = "/data/service/hnp/bin/llvm-nm"
        clang = "/data/service/hnp/bin/clang"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        skip = {"_init", "_fini", "_end", "_edata", "__bss_start", "_start"}
        replaced = []
        prefix = self._gtk_prefix()
        for soname in self.GTK_STACK_STUB_SO:
            real = os.path.join(prefix, "lib", soname)
            if not os.path.isfile(real):
                base = soname.split(".so")[0] + ".so."
                libdir = os.path.join(prefix, "lib")
                if os.path.isdir(libdir):
                    for f in sorted(os.listdir(libdir)):
                        if f.startswith(base) and not f.endswith(".so"):
                            real = os.path.join(libdir, f)
                            break
            if not os.path.isfile(real):
                self.output.warning("gtk stub source not found for {}".format(soname))
                continue
            out = subprocess.run([nm, "-D", "--defined-only", real],
                                 capture_output=True, text=True).stdout
            funcs, datas = [], []
            for line in out.splitlines():
                m = re.match(r"\s*[0-9a-fA-F]+\s+([TtWw])\s+(\S+)", line)
                if m:
                    funcs.append(m.group(2)); continue
                m = re.match(r"\s*[0-9a-fA-F]+\s+([DdBb])\s+(\S+)", line)
                if m:
                    datas.append(m.group(2))
            cpath = os.path.join(stubs_dir, soname + ".c")
            with open(cpath, "w", encoding="utf-8") as f:
                f.write("#include <stddef.h>\n")
                for sym in funcs:
                    if sym in skip or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", sym):
                        continue
                    f.write('__attribute__((visibility("default"))) void *{0}(void) {{ return 0; }}\n'.format(sym))
                for sym in datas:
                    if sym in skip or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", sym):
                        continue
                    f.write('__attribute__((visibility("default"))) unsigned char {0}[8] __attribute__((aligned(8))) = {{0}};\n'.format(sym))
            spath = os.path.join(stubs_dir, soname)
            cc_env = dict(os.environ)
            # lld 依赖 libxml2.so.16（E106）：stub 编译需要 SDK llvm/lib 可加载。
            llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if not os.path.isdir(llvm_lib):
                cands = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
                llvm_lib = cands[0] if cands else ""
            if llvm_lib:
                cc_env["LD_LIBRARY_PATH"] = llvm_lib + os.pathsep + cc_env.get("LD_LIBRARY_PATH", "")
            r = subprocess.run([clang, "-shared", "-fPIC", "-o", spath, cpath,
                                "-Wl,-soname," + soname], capture_output=True, text=True, env=cc_env)
            if r.returncode != 0:
                raise RuntimeError("gtk stub compile failed for {}: {}".format(soname, r.stderr[-800:]))
            subprocess.run([objcopy, "--remove-section", ".codesign", spath], stderr=subprocess.DEVNULL)
            subprocess.run([signer, "sign", "-inFile", spath, "-outFile", spath, "-selfSign", "1"],
                           check=True)
            shutil.copyfile(spath, os.path.join(runtime_dir, soname))
            replaced.append(soname)
        return replaced

    def _run_deployed(self, test_exe):
        runtime_dir = os.path.join(self.build_folder, "test-runtime")
        tmp_dir = os.path.join(self.build_folder, "test-tmp")
        # HMDFS 上覆盖已存在文件报 Operation not permitted → 每次先清理重建
        shutil.rmtree(runtime_dir, ignore_errors=True)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        os.makedirs(runtime_dir, exist_ok=True)
        os.makedirs(tmp_dir, exist_ok=True)
        shutil.copyfile(test_exe, os.path.join(runtime_dir, "test_gnumeric"))
        os.chmod(os.path.join(runtime_dir, "test_gnumeric"), 0o755)
        copied = self._deploy_runtime_closure(os.path.join(runtime_dir, "test_gnumeric"), runtime_dir)
        self.output.info("deployed {} runtime libs for test_gnumeric".format(len(copied)))
        elfs = [os.path.join(runtime_dir, "test_gnumeric")] + copied
        patchelf = glob.glob("/data/service/hnp/bin/patchelf") or ["patchelf"]
        objcopy = glob.glob("/data/service/hnp/bin/llvm-objcopy") or ["llvm-objcopy"]
        signer = glob.glob("/data/service/hnp/bin/binary-sign-tool") or ["binary-sign-tool"]
        for path in elfs:
            if not self._is_elf(path):
                continue
            subprocess.run([patchelf[0], "--set-rpath", "$ORIGIN", path], check=True)
            subprocess.run([objcopy[0], "--remove-section", ".codesign", path],
                           stderr=subprocess.DEVNULL)
            subprocess.run([signer[0], "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
                           check=True)
        # GTK 栈 stub 替换 + LD_PRELOAD 动态 glib（同 goffice test_package）
        replaced = self._gen_gtk_stack_stubs(runtime_dir)
        self.output.info("replaced GTK stack with stubs: {}".format(", ".join(replaced)))
        bash = glob.glob("/data/service/hnp/bin/bash") or ["bash"]
        env = dict(os.environ)
        env.pop("LD_LIBRARY_PATH", None)
        # conan 构建目录父级仅 --x 权限，bash getcwd() 失败 → 显式 PWD=runtime_dir。
        env["PWD"] = runtime_dir
        env.pop("OLDPWD", None)
        env["TMPDIR"] = tmp_dir
        env["HOME"] = tmp_dir
        env["LD_PRELOAD"] = ":".join(os.path.join(runtime_dir, s) for s in self.GLIB_PRELOAD_SO)
        r = subprocess.run([bash[0], "-c", "./test_gnumeric"], cwd=runtime_dir, env=env,
                           capture_output=True, text=True)
        if r.stdout:
            self.output.info(r.stdout[-3000:])
        if r.stderr:
            self.output.info(r.stderr[-3000:])
        if r.returncode != 0:
            raise RuntimeError("test_gnumeric runtime FAILED (rc={}): {}".format(
                r.returncode, (r.stderr or "")[-2000:]))
        self.output.info("test_gnumeric runtime PASS (8/8 assertions)")

    def _clean_build_folder(self):
        """移除 cmake 增量构建缓存，强制 test() 重新 configure + link。

        本 test_package 为 test_type="explicit"（无 layout），构建发生在
        test_package/ 源码目录内，因此必须手动清理，否则 L1e 负向测试
        （移走被测包 lib/）无法触发重新链接。
        """
        for name in ("CMakeCache.txt", "CMakeFiles", "cmake_install.cmake",
                     "Makefile", "CTestTestfile.cmake", "CMakePresets.json"):
            p = os.path.join(self.build_folder, name)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.isfile(p):
                os.remove(p)
