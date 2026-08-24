import os
import glob as _glob
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class RuamelYamlClibConan(ConanFile):
    name = "ruamel-yaml-clib"
    version = "0.2.15"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://sourceforge.net/p/ruamel-yaml/"
    description = ("ruamel.yaml C accelerator (libyaml port) — awscli "
                   "dependency chain L1 (C extension compiled on OHOS)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # 零依赖（PyPI requires_dist 核验：无——C 扩展自身无外部库依赖）

    def source(self):
        get(self, **self.conan_data["sources"]["ruamel-yaml-clib"],
            strip_root=True)

    def build(self):
        work = self.source_folder
        # C 扩展编译：clang 编译 9 个 .c 为 _ruamel_yaml.so
        # （libyaml 移植——无外部依赖——OHOS clang + Python 头）
        # Python 头/库路径动态获取（sysconfig——CI worker 是独立设备，
        # 无本机 /storage/Users/currentUser/usr/local 路径——硬编码实测
        # Python.h missing）；候选位置兜底（/data/app、/system、
        # usr/local——覆盖 CI worker 与本机两种环境）
        import sysconfig
        py_inc = sysconfig.get_paths().get("include", "")
        py_lib = sysconfig.get_config_var("LIBDIR") or ""
        if not os.path.isfile(os.path.join(py_inc, "Python.h")):
            for cand in ("/data/app/include/python3*",
                         "/system/include/python3*",
                         "/storage/Users/currentUser/usr/local/include/"
                         "python3*"):
                hits = _glob.glob(cand)
                for h in hits:
                    if os.path.isfile(os.path.join(h, "Python.h")):
                        py_inc = h
                        break
                if os.path.isfile(os.path.join(py_inc, "Python.h")):
                    break
        if not os.path.isfile(os.path.join(py_inc, "Python.h")):
            raise ConanException(f"Python.h missing (py_inc={py_inc})")
        # py_lib 同样需要候选兜底（CI worker 的 sysconfig LIBDIR 指向
        # usr/local/lib 但无 libpython3*.so 实测——'libpython3*.so
        # missing (py_lib=.../usr/local/lib)' #29958/#30223/#30245）——
        # 本机实测 .so 与 .so.1.0 共存、LIBPL 下有 .a——策略：
        # ①sysconfig 全量探测打印（供 CI 诊断）②直接目录候选（无
        # python3 子目录）③find 全盘兜底 ④.so 与 .a 兼容
        _cfg_info = {k: sysconfig.get_config_var(k) for k in
                     ("LIBDIR", "LIBPL", "LDLIBRARY", "LIBRARY",
                      "prefix", "base", "platbase")}
        self.output.info(f"sysconfig 探测: {_cfg_info}")
        _base = sysconfig.get_config_var("base") or ""
        _plat = sysconfig.get_config_var("platbase") or ""
        lib_cands = [py_lib,
                     sysconfig.get_config_var("LIBPL") or "",
                     os.path.join(sysconfig.get_config_var("prefix")
                                  or "", "lib"),
                     # CI worker 的 base/platbase 指向应用目录（日志实测
                     # base=/data/service/hnp/.../ci_o.../）——libpython
                     # 在其 lib/ 下
                     os.path.join(_base, "lib"),
                     os.path.join(_base, "lib64"),
                     os.path.join(_plat, "lib"),
                     os.path.join(_plat, "lib64"),
                     "/data/app/lib",
                     "/data/app/lib64",
                     "/system/lib",
                     "/system/lib64",
                     "/system/usr/lib64",
                     "/vendor/lib64",
                     "/storage/Users/currentUser/usr/local/lib"]
        found_lib = None
        # 候选：.so* 优先，其次 .a（本机 LIBPL 实测仅 .a）
        for pat in ("libpython3*.so*", "libpython3*.a"):
            if found_lib:
                break
            for cand in lib_cands:
                if not cand or not os.path.isdir(cand):
                    continue
                hits = _glob.glob(os.path.join(cand, pat))
                if hits:
                    found_lib = hits[0]
                    break
        # find 全盘兜底（CI worker 库位置未知——/data /system /vendor）
        if not found_lib:
            try:
                r = subprocess.run(
                    ["find", "/data", "/data/service", "/system",
                     "/vendor", "/storage/Users/currentUser",
                     "-maxdepth", "6", "-name", "libpython3*.so*"],
                    capture_output=True, text=True, timeout=60)
                for line in r.stdout.splitlines():
                    if line.strip() and os.path.isfile(line.strip()):
                        found_lib = line.strip()
                        break
            except Exception:
                pass
        if found_lib:
            py_lib = os.path.dirname(found_lib)
        if not _glob.glob(os.path.join(py_lib, "libpython3*.so*")) and \
           not _glob.glob(os.path.join(py_lib, "libpython3*.a")):
            raise ConanException(
                f"libpython3*.so missing (py_lib={py_lib}, "
                f"sysconfig={_cfg_info})")
        srcs = [os.path.join(work, f) for f in
                ("_ruamel_yaml.c", "api.c", "dumper.c", "emitter.c",
                 "loader.c", "parser.c", "reader.c", "scanner.c",
                 "writer.c")]
        out = os.path.join(work, "_ruamel_yaml.so")
        pyver = "python%d.%d" % sys.version_info[:2]
        r = subprocess.run(
            ["/data/service/hnp/bin/clang", "-shared", "-fPIC",
             "-O2", "-Wno-macro-redefined", "-I" + py_inc,
             "-L" + py_lib, "-DHAVE_CONFIG_H"] + srcs +
            ["-l" + pyver, "-o", out],
            capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise ConanException(
                f"C extension build failed: {r.stderr[:500]}")
        if not os.path.isfile(out):
            raise ConanException("_ruamel_yaml.so not produced")

    def package(self):
        work = self.source_folder
        pyver = "python%d.%d" % sys.version_info[:2]
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        # ruamel.yaml.clib 装为 ruamel/yaml/clib/（命名空间子包）
        pkg_dst = os.path.join(site, "ruamel", "yaml", "clib")
        os.makedirs(pkg_dst, exist_ok=True)
        shutil.copy2(os.path.join(work, "_ruamel_yaml.so"),
                     os.path.join(pkg_dst, "_ruamel_yaml.so"))
        shutil.copy2(os.path.join(work, "__init__.py"),
                     os.path.join(pkg_dst, "__init__.py"))
        # 命名空间包 __init__.py（ruamel/ 与 ruamel/yaml/）
        for ns in ("ruamel", os.path.join("ruamel", "yaml")):
            ns_init = os.path.join(site, ns, "__init__.py")
            os.makedirs(os.path.dirname(ns_init), exist_ok=True)
            if not os.path.isfile(ns_init):
                open(ns_init, "w").write("")
        if not os.path.isfile(os.path.join(pkg_dst, "_ruamel_yaml.so")):
            raise ConanException("_ruamel_yaml.so missing in package")

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
