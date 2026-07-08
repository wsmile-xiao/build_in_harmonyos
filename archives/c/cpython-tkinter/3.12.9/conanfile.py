from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches
import os
import glob
import json
import shutil
import subprocess


class CPythonTkinterConan(ConanFile):
    """CPython 3.12.9 的 _tkinter C 扩展 → 鸿蒙 PC(os=OHOS arch=armv8)。

    产物：_tkinter.cpython-312-aarch64-linux-ohos.so，打进 lib/python3.12/lib-dynload/，
    配 usr_local deployer 直接落到 ~/usr/local/lib/python3.12/lib-dynload/。
    依赖 tcl/tk 9.0.3(conan requires)；Python dev 头/libpython 由设备 python3 的 sysconfig 自发现
    (须与目标 runtime 同版本 3.12.9——_tkinter 与 CPython ABI 锁死)。
    源为 vendored 快照：CPython v3.12.9 的 Modules/{_tkinter.c,tkinter.h,clinic/_tkinter.c.h}
    (该版本已 backport tcl9)。tk.h 需的 <X11/Xlib.h> 等 X11 stub 头由 tk 包 include/X11/ 提供
    (tk 9.0.3.1 起随包装)。
    """
    name = "cpython-tkinter"
    version = "3.12.9"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "src/*"

    def export_sources(self):
        pass

    def source(self):
        pass

    def requirements(self):
        self.requires("tcl/9.0.3.1")
        self.requires("tk/9.0.3.1")

    # --- 找目标 python3（PATH 无关：CI 构建环境常不把 python3 放进 PATH，但 HOME 有设）---
    # 优先各环境提供的「完整」python：CI 用 which 得到的 hnp python（带 dev 头 + 共享 libpython），
    # 设备用 ~/usr/local 的 python。CI 的 ~/usr/local 可能是残缺装（有头无 libpython），故不强选它。
    def _python3(self):
        import shutil
        cands = [os.environ.get("TKINTER_PYTHON"),
                 shutil.which("python3"),                          # 各环境提供的完整 python
                 os.path.expanduser("~/usr/local/bin/python3"),
                 "/usr/local/bin/python3", "/usr/bin/python3"]
        for c in cands:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration(
            "找不到 python3：设 TKINTER_PYTHON=<路径>，或把带 dev 头的 CPython 3.12 装到 ~/usr/local")

    # --- 自发现目标 Python 的 dev 环境(sysconfig) ---
    def _py(self):
        py = self._python3()
        # 除 sysconfig 外，还从 /proc/self/maps 问「解释器本进程实际加载的 libpython 路径」——这是 ground
        # truth：共享构建的 python 一定把 libpython 映进了自己进程，且该 SONAME 与运行期一致。比信 sysconfig
        # LIBDIR 靠谱（CI 的 hnp python 的 LIBDIR 错位、指向没有 libpython 的目录）。
        code = ("import sysconfig,sys,json,os;"
                "d=dict(inc=sysconfig.get_paths()['include'],"
                "libdir=sysconfig.get_config_var('LIBDIR'),"
                "libpl=sysconfig.get_config_var('LIBPL'),"
                "prefix=sys.base_prefix,"
                "ext=sysconfig.get_config_var('EXT_SUFFIX'),"
                "ver=sysconfig.get_python_version());"
                "m=[l.split()[-1] for l in open('/proc/self/maps') if 'libpython3.12.so' in l] "
                "if os.path.exists('/proc/self/maps') else [];"
                "d['libpython']=m[0] if m else '';"
                "print(json.dumps(d))")
        info = json.loads(subprocess.check_output([py, "-c", code]).decode())
        if info["ver"] != "3.12":
            raise ConanInvalidConfiguration(
                "目标 python3 是 {}，本包锁定 3.12(_tkinter 与 CPython ABI 锁死)".format(info["ver"]))
        if not os.path.isfile(os.path.join(info["inc"], "internal", "pycore_long.h")):
            raise ConanInvalidConfiguration(
                "缺 Python internal 头({}/internal/pycore_long.h)——需带 dev 头的 CPython".format(info["inc"]))
        info["libpython"] = self._libpython_file(py, info)
        return info

    # 定位一个可链接的 libpython 完整文件（直接喂给链接器，不走 -L/-l，免去「目录里要有 .so 软链」的依赖；
    # 链接器读其 DT_SONAME 记成 NEEDED=libpython3.12.so.1.0，运行期按 SONAME 解析）。扩展必须链 libpython
    # （OHOS/musl 下 Py* 不进全局符号表，不链则 import 段错误，ML-0008）。优先解释器自报的实际加载路径。
    def _libpython_file(self, py, info):
        lp = info.get("libpython") or ""
        if lp and os.path.isfile(lp):
            return lp                            # 解释器实际加载的 libpython —— ground truth
        py_prefix_lib = os.path.join(os.path.dirname(os.path.dirname(py)), "lib")
        checked = [info.get("libpl"), info.get("libdir"),
                   os.path.join(info.get("prefix", ""), "lib"), py_prefix_lib,
                   os.path.expanduser("~/usr/local/lib"), "/usr/local/lib"]
        for d in checked:
            if not d:
                continue
            hits = (glob.glob(os.path.join(d, "libpython3.12.so"))
                    or glob.glob(os.path.join(d, "libpython3.12.so*")))
            if hits:
                return hits[0]
        # 兜底：在 python 前缀 / ~/usr/local 下 find
        import subprocess
        for r in (info.get("prefix"), os.path.dirname(os.path.dirname(py)),
                  os.path.expanduser("~/usr/local")):
            if r and os.path.isdir(r):
                try:
                    out = subprocess.check_output(
                        ["find", r, "-name", "libpython3.12.so*"],
                        stderr=subprocess.DEVNULL, timeout=30).decode().split()
                except Exception:
                    out = []
                if out:
                    return out[0]
        raise ConanInvalidConfiguration(
            "找不到 libpython3.12.so（扩展须链 libpython，OHOS/musl 下 Py* 不进全局符号表，ML-0008）。"
            "python={}；/proc/self/maps 未见 libpython；查过 {}；在 prefix/~/usr/local 下 find 亦空。"
            .format(py, checked))

    def _cc(self):
        execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return execs.get("c", "clang")

    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "src")
        py = self._py()
        tcl = self.dependencies["tcl"].cpp_info
        tk = self.dependencies["tk"].cpp_info
        out = os.path.join(self.build_folder, "_tkinter" + py["ext"])
        # 原生 clang 编译 _tkinter.c(链接器自动自签，ML-0043)。
        # 必须显式链 libpython：OHOS/musl 下嵌入解释器以 RTLD_LOCAL 加载扩展，Py* 符号不进全局符号表
        # (ML-0008)，不链则 import 段错误。直接把 libpython 完整文件喂链接器（见 _py 的 libpython，免 .so 软链依赖）。
        cmd = [
            self._cc(), "-shared", "-fPIC", "-DPy_BUILD_CORE_MODULE",
            "-I" + src,
            "-I" + py["inc"], "-I" + os.path.join(py["inc"], "internal"),
        ]
        cmd += ["-I" + d for d in tcl.includedirs]
        cmd += ["-I" + d for d in tk.includedirs]   # tk 包已含 include/X11（tk.h 需 <X11/Xlib.h>）
        cmd += [os.path.join(src, "_tkinter.c")]
        cmd += [py["libpython"]]
        cmd += ["-L" + tcl.libdirs[0], "-ltcl9.0"]
        cmd += ["-L" + tk.libdirs[0], "-ltcl9tk9.0"]
        cmd += ["-o", out]
        self.run(" ".join('"{}"'.format(c) if " " in c else c for c in cmd))
        self._ext = os.path.basename(out)

    def package(self):
        # 落进 lib/python3.12/lib-dynload/ —— usr_local deployer 直接铺进 ~/usr/local 对应位置。
        # .so 靠链接器自签（干净 .so 独立 dlopen 有效，ML-0043）；真机 HiShell 域实测 import 通过。
        dst = os.path.join(self.package_folder, "lib", "python3.12", "lib-dynload")
        os.makedirs(dst, exist_ok=True)
        for so in glob.glob(os.path.join(self.build_folder, "_tkinter*.so")):
            shutil.copy2(so, os.path.join(dst, os.path.basename(so)))

    def package_info(self):
        # 纯 CPython 扩展模块：不给别的库链接，无公开头。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
