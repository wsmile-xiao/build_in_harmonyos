# cpython-tkinter/3.12.9 — 鸿蒙 PC _tkinter conan 包

CPython 3.12.9 的 `_tkinter` C 扩展(桥接 Python 到 Tcl/Tk 9.0.3)做成鸿蒙 PC conan 制品。

## 出包(鸿蒙 PC 原生)
```bash
conan create . -pr ohos-native
```
- `requires tcl/9.0.3.1 tk/9.0.3.1`(conan 自动拉，提供头+库)。
- Python dev 头/libpython 由**设备 python3 的 sysconfig 自发现**(须 3.12.x，_tkinter 与 CPython ABI 锁死)；可用 `TKINTER_PYTHON` 覆盖。
- 源为 vendored 快照：CPython v3.12.9 `Modules/{_tkinter.c,tkinter.h,clinic/_tkinter.c.h}` ；tk.h 需的 X11 头由 tk 包 `include/X11/` 提供(tk 9.0.3.1 起随包)。
- 产物 `_tkinter.cpython-312-aarch64-linux-ohos.so` 打进 `lib/python3.12/lib-dynload/`；原生构建链接器自签(ML-0043)。

## 消费(部署到设备)
```bash
conan install --requires cpython-tkinter/3.12.9@ohpcd/stable tcl/9.0.3.1@ohpcd/stable tk/9.0.3.1@ohpcd/stable \
  -pr ohos-native --deployer=usr_local --deployer-folder=$HOME/usr/local
```
`usr_local` deployer 会把 `_tkinter.so` 铺进 `~/usr/local/lib/python3.12/lib-dynload/`、tcl/tk 铺进 `~/usr/local/lib`。

## 运行期契约
- `LD_LIBRARY_PATH=~/usr/local/lib`(找 libtcl/libtk/libpython)
- `TCL_LIBRARY=~/usr/local/lib/tcl9.0`、`TK_LIBRARY=~/usr/local/lib/tk9.0`(脚本库)
- 之后 `import tkinter` 即可(真机实测：import _tkinter=9.0 9.0、tkinter.Tk()=TK_OK)。
