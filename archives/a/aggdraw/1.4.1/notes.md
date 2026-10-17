# aggdraw 1.4.1

aggdraw is a CPython C++ extension exposing anti-aliased vector drawing
primitives.  Version 1.4.1 requires Python 3.11 or newer and is built by
setuptools.

## Source and dependencies

- Upstream: https://github.com/pytroll/aggdraw
- Source archive: PyPI sdist, fixed by SHA256 in `conandata.yml`.
- W0 dependency check: no Conan dependencies are declared by this recipe.
- The sdist contains no upstream test directory or `make test`/CTest target.

## Packaging

The recipe builds the C++ extension through the device Python and installs it
to a package-local staging directory.  `package_info()` exposes that directory
through `PYTHONPATH`, so the consumer test imports the packaged extension rather
than the source tree.

The OHOS CI SDK `lld` loads an incompatible `libxml2.so.16`, so the recipe
selects the HNP linker through `-fuse-ld=/data/service/hnp/bin/ld`.

## Consumer test

`test_package/test_aggdraw.py` imports the packaged native module, checks its
version, builds a closed vector path, and creates Pen and Brush objects.

## 鸿蒙真机适配（5 处拦点）

aggdraw 上游是纯 setuptools 配方，鸿蒙真机 + CI 复验撞 5 处鸿蒙特定拦点，配方在 `build()` / `package()` / `test_package test()` 段用环境变量 + ELF 重签名绕法处理：

| # | 拦点 | 根因 | 修法 |
|---|---|---|---|
| 1 | `command 'c++' failed: No such file or directory` | �鸿蒙 python_3.12 编译时把 `CXX="c++"` 硬编码进 sysconfig；setuptools build_ext 走 `sysconfig.get_config_var('CXX')` 拿 `c++` 当编译器名，但真机 PATH 只装了 `clang`/`clang++`、无 `c++` 软链接 | `build()` 段命令行内联 `env CXX=clang++` 覆盖 sysconfig 默认（同 `LDSHARED` 也从硬编码的 `cc -shared` 换成 `clang++ -shared`） |
| 2 | `ImportError: Error relocating aggdraw.cpython-312.so: PyModule_Create2: symbol not found` | �鸿蒙 python3.12 主程**静态编进 libpython**、不 export Python C-API 符号给 extension；aggdraw.so 的 NEEDED 只有 `libc++_shared.so`/`libc.so`，运行时找 `PyModule_Create2` 就空 | `build()` 段给 `LDSHARED` + `LDFLAGS` 加 `-L<python_lib_dir> -lpython3.12`，让 aggdraw.so 链鸿蒙自带的 `libpython3.12.so`（它真 export `PyModule_Create2`：`nm -D` 显 `0000000000291288 T PyModule_Create2`），符号运行时从 libpython3.12.so 找到 |
| 3 | `ModuleNotFoundError: No module named 'aggdraw'` | 上游 `test()` 段用 conan `self.run(..., env=[f"PYTHONPATH={package_folder}"])` 注环境变量，但 conan `self.run` 的 `env` 参数只接预定义 scope 名（`conanrun`/`conanbuild`），不接 `["PYTHONPATH=..."]` 列表 | `test()` 段命令行内联 `env PYTHONPATH=<package_folder> python3 test_aggdraw.py` 绕 conan `self.run` env 参数限制 |
| 4 | `cannot find -lpython3.12`（CI 环境） | 旧配方 `py_lib_dir = abspath(dirname(sys.executable)/../lib)` 在真机恰好命中 `/data/service/hnp/python.org/python_3.12/lib`，但 CI 的 libpython3.12.so 不在该相对路径下；硬编码绝对 `/data/service/hnp/lib` 同样不可移植 | `build()` 段改用 `py_lib_dir = os.path.join(sys.prefix, "lib")`——`sys.prefix` 是运行中 Python 的安装根（真机 `.../python_3.12`、CI 各异），libpython 装在 `<prefix>/lib/libpython3.12.so`。`sysconfig.get_config_var('LIBDIR')` 不可用（返回 `/python3/lib`，是 python.org 编译时 DESTDIR 暂存残留） |
| 5 | `ImportError: Error loading shared library aggdraw.cpython-312.so: Permission denied` | 鸿蒙 MAC（`hmmac=use_task`）拒执行未签名 ELF；aggdraw.so 装入 conan cache `p/` 后 `import aggdraw` 被拦 | `package()` 段对最终 `aggdraw.cpython-312.so` 做 ELF 重签名：`llvm-objcopy --remove-section .codesign`（容首次无段）+ `binary-sign-tool sign -selfSign 1` + `os.replace` 原子替换 + `chmod 0o755`，同仓库 daemon/ent/zig/ispell 模式 |

另：aggdraw setup.py 的 freetype 探测**非致命**——`=== freetype not available` 是警告、extension �照编（只是关字体支持），鸿蒙真机无 freetype-config/pkgconfig 也能编，故配方未声明 freetype 依赖。

另：CI 的 SDK `lld` 链一个不兼容的 `libxml2.so.16`，故 `LDSHARED`/`LDFLAGS` 用 `-fuse-ld=/data/service/hnp/bin/ld` 选 HNP 链接器（真机环境无此问题但留着不碍）。

## 复检修正（2 处）

首轮 fix 推送后用户复检到两个真问题，本轮修正：

| # | 复检拦点 | 根因 | 修正 |
|---|---|---|---|
| 6 | `package()` 只查固定 `aggdraw.cpython-312.so`，CI 实际生成 `aggdraw.cpython-312-aarch64-linux-ohos.so`，ELF 重签名静默跳过、MAC 修复未执行 | wheel build 把 `.so` 名带上平台 ABI 标签（CI `-aarch64-linux-ohos`、真机不带），固定名 `os.path.isfile()` 在 CI 命中失败 → `if` 段整段跳过 | `package()` 改用 `glob.glob(<pkg>/aggdraw*.so)` 通配匹配每个真 ELF 产物签名，不再固定名；命中失败不再静默跳过 |
| 7 | `commands.json` 缺 CI 要求的 `"type": "tool"` 字段，L0 警告 | aggdraw 配方目录根本无 `commands.json`（find 空），CI L0 检查要该文件含 `"type": "tool"` 声明 | 新建 `archives/a/aggdraw/1.4.1/commands.json`，参照仓库 bam/ansifilter 等配方格式：`name`/`description`/`homepage`/`"type": "tool"`/`versions` 段含 `ref`+`binary:false` |

## 构建状态

- [x] SHA256 已填写
- [x] W0 依赖检查通过（无 Conan 依赖）
- [x] conan create 通过（exit 0、aggdraw.cpython-312.so 真编出来）
- [x] test_package 执行通过（`aggdraw native Path/Pen/Brush API: PASSED`）
- [x] aggdraw.so 链 libpython3.12.so（PyModule_Create2 符号运行时解析）
- [x] 鸿蒙真机复验通过（HarmonyOS HongMeng Kernel 1.12.0 aarch64, clang 15.0.4, python 3.12）
