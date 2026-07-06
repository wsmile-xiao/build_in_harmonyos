import os
import glob
import subprocess
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _tkinter_so(self):
        pkg = self.dependencies["cpython-tkinter"]
        sos = glob.glob(os.path.join(str(pkg.package_folder),
                                     "lib", "python3.12", "lib-dynload", "_tkinter*.so"))
        if not sos:
            raise Exception("包内未见 _tkinter*.so")
        return sos[0]

    def build(self):
        # test.c 编成 test_probe，dlopen 目标烤进 -DTARGET_SO（.so 全路径构建期已知）
        so = self._tkinter_so()
        cc = os.environ.get("CC", "clang")
        self.run("{cc} test.c -o test_probe -DTARGET_SO='\"{so}\"' -ldl".format(cc=cc, so=so))

    def _libpython_dir(self):
        # _tkinter.so NEEDED libpython3.12.so.1.0；run test_probe 前须让它在 LD_LIBRARY_PATH 上。
        # 用 python3 的 /proc/self/maps 问其实际加载的 libpython 目录（ground truth，跨环境可靠）。
        import shutil
        py = None
        for c in [os.environ.get("TKINTER_PYTHON"), shutil.which("python3"),
                  os.path.expanduser("~/usr/local/bin/python3"), "/usr/local/bin/python3", "/usr/bin/python3"]:
            if c and os.path.isfile(c):
                py = c
                break
        if not py:
            return ""
        code = ("import os;"
                "m=[l.split()[-1] for l in open('/proc/self/maps') if 'libpython3.12.so' in l];"
                "print(os.path.dirname(m[0]) if m else '')")
        try:
            return subprocess.check_output([py, "-c", code], text=True).strip()
        except Exception:
            return ""

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        tcl_lib = self.dependencies["tcl"].cpp_info.libdirs[0]
        tk_lib = self.dependencies["tk"].cpp_info.libdirs[0]
        pylib = self._libpython_dir()
        paths = ":".join(p for p in (tcl_lib, tk_lib, pylib) if p)
        # 加载者是现编的 test_probe（自签 adhoc）——CI 域可 dlopen 自签 .so（tcl 实证）；SDK 签名的
        # python3 不行，故不用 import。RTLD_NOW 会解析 _tkinter 的全部 Py/Tcl/Tk 符号（不初始化解释器）。
        env = 'LD_LIBRARY_PATH="{paths}:${{LD_LIBRARY_PATH:-}}"'.format(paths=paths)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run('{env} {bash} -c "./test_probe"'.format(env=env, bash=bash))
