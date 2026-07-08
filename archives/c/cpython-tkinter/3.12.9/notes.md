# cpython-tkinter 3.12.9 — 适配笔记

## 软件
CPython 3.12.9 的 `_tkinter` C 扩展模块，桥接 Python 到 Tcl/Tk 9.0.3。

## 构建方式
- 源码为 vendored 快照：CPython v3.12.9 的 `Modules/{_tkinter.c,tkinter.h,clinic/_tkinter.c.h}`
- 原生 clang 编译 `_tkinter.c` → `_tkinter.cpython-312-aarch64-linux-ohos.so`
- 链接：libpython3.12.so（系统 Python 自发现）、libtcl9.0、libtcl9tk9.0（Conan 依赖）

## 依赖
- `tcl/9.0.3.1`（Conan 制品仓）
- `tk/9.0.3.1`（Conan 制品仓）
- Python 3.12.9 dev 头 + libpython（系统运行时依赖，sysconfig 自发现）

## 关键决策
1. **不通过 Conan 管理 Python 依赖**：_tkinter 与 CPython ABI 锁死，必须链设备上实际运行的 libpython
2. **显式链 libpython**：OHOS/musl 下 Py* 符号不进全局符号表（ML-0008），不链则 import 段错误
3. **直接把 libpython 完整文件喂链接器**：免 .so 软链依赖，链接器读 DT_SONAME 记成 NEEDED
4. **source() 为 no-op**：源码 vendored 在 src/，通过 exports_sources 导出

## conandata.yml
- URL 指向 CPython 3.12.9 官方 tarball（溯源元数据）
- sha256 已验证：`29a9062207e0d10d2fb08209454803ec98bcc0ab9204baee1ccf48a6e812eb72`
- source() 不使用 conandata 下载（vendored 模式）

## 验证结果
- conan-verify: G1-G4 + L2/L4/L5 全通过 ✅
- 产物：`_tkinter.cpython-312-aarch64-linux-ohos.so` → `lib/python3.12/lib-dynload/`
