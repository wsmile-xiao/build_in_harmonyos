import os
import glob
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：跳过运行期 import")
            return
        pkg = self.dependencies["cpython-tkinter"]
        sos = glob.glob(os.path.join(str(pkg.package_folder),
                                     "lib", "python3.12", "lib-dynload", "_tkinter*.so"))
        if not sos:
            raise Exception("包内未见 _tkinter*.so")
        so_dir = os.path.dirname(sos[0])
        tcl = self.dependencies["tcl"].cpp_info
        tk = self.dependencies["tk"].cpp_info
        tcl_lib = tcl.libdirs[0]
        tk_lib = tk.libdirs[0]
        # 脚本库：tcl/tk 包的 lib/tcl9.0 与 lib/tk9.0
        tcl_root = os.path.dirname(tcl_lib) if os.path.basename(tcl_lib) == "lib" else str(self.dependencies["tcl"].package_folder)
        tk_root = str(self.dependencies["tk"].package_folder)
        env = (
            'PYTHONPATH="{sd}" '
            'LD_LIBRARY_PATH="{tcll}:{tkl}:${{LD_LIBRARY_PATH:-}}" '
            'TCL_LIBRARY="{tclr}/lib/tcl9.0" '
            'TK_LIBRARY="{tkr}/lib/tk9.0" '
        ).format(sd=so_dir, tcll=tcl_lib, tkl=tk_lib, tclr=tcl_root, tkr=tk_root)
        # PATH 无关地找 python3（CI 构建环境常不把 python3 放进 PATH，但 HOME 有设）
        import shutil
        py = None
        for c in [os.environ.get("TKINTER_PYTHON"), shutil.which("python3"),
                  os.path.expanduser("~/usr/local/bin/python3"), "/usr/local/bin/python3", "/usr/bin/python3"]:
            if c and os.path.isfile(c):
                py = c
                break
        test_py = os.path.join(self.source_folder, "test.py")
        self.run(env + py + ' "' + test_py + '"')
