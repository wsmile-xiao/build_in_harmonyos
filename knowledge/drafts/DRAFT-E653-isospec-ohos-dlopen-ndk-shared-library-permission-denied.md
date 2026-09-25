# E653 — OHOS dlopen 拒载 NDK 本机构建共享库（Permission denied 的真实边界）

- 来源任务：`feat/isospec-2.3.2`（IsoSpec++ 2.3.2，2026-09-21，鸿蒙 PC 设备单端实测）
- 错误签名：`OSError: cannot load library 'lib*.so': Error loading shared library ...: Permission denied`
- 配套条目：`DRAFT-E653-isospec-ohos-dlopen-ndk-shared-library-permission-denied.kv`

## 现象

IsoSpec 2.3.2 的 PyPI 绑定（scikit-build-core + cffi，`IsoSpecPy`）在设备上现场构建
wheel 成功（`isospecpy-2.3.2-cp312-cp312-ohos_aarch64.whl`），pip 安装成功，但
`import IsoSpecPy` 时 cffi `dlopen` 报：

```
OSError: cannot load library '.../site-packages/IsoSpecPy/libIsoSpecCppPy.so':
Error loading shared library .../libIsoSpecCppPy.so: Permission denied.
```

同一目录、同一属主、同为 pip 解压安装的 `_cffi_backend.cpython-312-aarch64-linux-ohos.so`
能正常 dlopen。

## 逐因子排除（实测矩阵）

| # | 假设 | 实验 | 结果 |
|---|---|---|---|
| 1 | 路径 noexec | cp 到应用沙箱 `/data/storage/el2/base/haps/entry/files`、`$TMPDIR`、`/dev/shm` 各试 dlopen | 全 DENIED；但同 HMDFS 的预编译扩展 OK → 非路径 |
| 2 | 文件名模式 | 改名为 `_renamed.cpython-312-aarch64-linux-ohos.so` | DENIED → 非文件名 |
| 3 | 依赖解析 | NEEDED=`libc++_shared.so`（OHOS 系统不存在，系统只有 `libc++.so`）；LD_LIBRARY_PATH 指 SDK 目录无效；`llvm-readelf` 原地改写 `.dynstr` 把 NEEDED 改为 `libc++.so`；`libc++_shared.so` 旁置 `$ORIGIN` | 四项实验后仍 DENIED → 非单靠依赖 |
| 4 | 16K LOAD 对齐 | R-E 段 0x1000（NDK）vs 0x4000（可载扩展）；`CXXFLAGS="-Wl,-z,max-page-size=16384"` 重链成 0x4000 | 仍 DENIED → 对齐是必要非充分 |
| 5 | 写者/内容 | `cp` 与 python `open().write()` 两种写者都 DENIED；社区 wheel 解压的扩展 OK | ELF 内容级拒载（NDK 产物带 `.note.ohos.ident` 等），设备策略下无用户侧修法 |

对照组：`execve` 路径（fork+exec 直接跑 NDK 编译的可执行文件，如 main_test 全套）
在设备上完全正常——**只有 dlopen 映射路径受此策略约束**。

## 有效修复（配方层，确定必要）

OHOS 共享产物一律加 16K 对齐 flag（OHOS 16K 页内核设备的官方要求）：

```python
# conanfile.py generate()
if self.settings.os == "OHOS":
    tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,-z,max-page-size=16384"
    tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = "-Wl,-z,max-page-size=16384"
    tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,-z,max-page-size=16384"
```

## 无效但值得记录的中间结论

- `LD_LIBRARY_PATH` 对 OHOS loader 的 dlopen 依赖解析**不生效**（与 profile [buildenv] 的
  链接期用途不同，别混淆）。
- 报错文案的「主库路径 Permission denied」是**误指**：真实失败可能在依赖解析（NEEDED 的
  `libc++_shared.so` 系统不存在）或内容级拒载；诊断时先 `llvm-readelf -d` 看 NEEDED。

## 对测试申报的影响

依赖现场 dlopen 的绑定层测试（pytest 消费 cffi/ctypes 的用例）在设备只能 NOT_RUN：
- 申报口径：环境限制 + 本条根因 + dlopen 探针日志；
- 核心功能改由 C++/C 消费者测试覆盖（本任务：main_test 1276+1144 全过、C wrapper 2/2 过）。

## 复现命令（设备可直接执行）

```sh
python3 -c "import ctypes; ctypes.CDLL('/path/to/ndk-built.so')"
# DENIED = 命中本条；再用下面两条取证
/data/service/hnp/bin/llvm-readelf -lW /path/to/ndk-built.so | grep 'R E'
/data/service/hnp/bin/llvm-readelf -d /path/to/ndk-built.so | grep NEEDED
```
