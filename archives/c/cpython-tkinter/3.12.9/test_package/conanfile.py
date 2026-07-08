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

    def _check_needed(self, so):
        """readelf -d 静态验证 .so 的 NEEDED 依赖链（CI fallback，test_probe 不可执行时用）。"""
        out = subprocess.check_output(["readelf", "-d", so], text=True, stderr=subprocess.DEVNULL)
        needed = [l.strip() for l in out.splitlines() if "NEEDED" in l]
        self.output.info("readelf NEEDED entries:\n  " + "\n  ".join(needed))
        sons = " ".join(needed)
        for lib in ["libpython3.12.so", "libtcl9.0.so", "libtcl9tk9.0.so"]:
            if lib not in sons:
                raise Exception(f"NEEDED 缺失: {lib}")
        self.output.info("readelf 静态检查通过: libpython + libtcl + libtk 均在 NEEDED")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        so = self._tkinter_so()
        tcl_lib = self.dependencies["tcl"].cpp_info.libdirs[0]
        tk_lib = self.dependencies["tk"].cpp_info.libdirs[0]
        pylib = self._libpython_dir()
        paths = ":".join(p for p in (tcl_lib, tk_lib, pylib) if p)
        env = 'LD_LIBRARY_PATH="{paths}:${{LD_LIBRARY_PATH:-}}"'.format(paths=paths)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            # test_probe dlopen(_tkinter.so, RTLD_NOW) 验证全部 Py/Tcl/Tk 符号解析
            self.run('{env} {bash} -c "./test_probe"'.format(env=env, bash=bash))
        except Exception as e:
            if "Operation not permitted" in str(e):
                self.output.info("test_probe 不可执行（CI 安全策略），fallback readelf -d 静态检查")
                self._check_needed(so)
            else:
                raise
