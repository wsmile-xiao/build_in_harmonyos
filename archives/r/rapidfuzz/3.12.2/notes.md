# rapidfuzz 3.12.2 适配笔记

## 编译环境
- 构建系统: cmake (Cython 预生成 .cxx, 无需 Cython)
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15 (aarch64-linux-ohos)
- 状态: built
- 上游版本: 3.12.2 (PyPI 官方 sdist, SHA-256 b0ba1ccc22fff782e7152a3d3d0caca44ec4e32dc48ba01c560b8593965b5aa3)

## 上游版本溯源

- `rapidfuzz` 3.12.2 是 **Python 包**（PyPI 名 `RapidFuzz`），上游仓库 <https://github.com/rapidfuzz/RapidFuzz>。
- 其 C++ 核心以 git submodule 形式 vendored 在 `extern/rapidfuzz-cpp`（版本 3.2.0）与 `extern/taskflow`。
- 上游 `rapidfuzz/rapidfuzz-cpp` 仓库的独立 release 线止于 **v3.3.4**（47 个 tag，最大 v3.3.4），
  已在本仓发布为 `archives/r/rapidfuzz-cpp/3.3.4`（status: published）。
- 因此 `rapidfuzz/3.12.2` 的交付物 = CPython 扩展模块 + 纯 Python 层；C++ 核心版本仍为 vendored 3.2.0。

## 编译步骤

```bash
# Conan 配方验证 (ohos-aarch64-wsl profile)
conan create archives/r/rapidfuzz/3.12.2 \
    -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl \
    --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(Python ...)` 报 `Could NOT find Python (missing: Interpreter Development.Module)` | CMake FindPython 在 cross-compiling 模式下拒绝运行解释器获取版本/SOABI；未指定 `Python_FIND_VERSION` 时版本探测失败 | **不设置 `CMAKE_SYSTEM_NAME`**，使 `CMAKE_CROSSCOMPILING=FALSE`；解释器可经 qemu-aarch64 binfmt 运行，FindPython 自动获取 3.12.9 + SOABI。OHOS 目标由 clang shim 强制 `--target=aarch64-linux-ohos` 保证 |
| 2 | taskflow `CheckAtomic.cmake` 报 `Host compiler appears to require libatomic` | 本地 WSL 的 clang shim 没有 C++ 标准库头文件搜索路径，`#include <atomic>` 失败 | 探测编译器 `-print-resource-dir` 推出 `<llvm>/include/c++/v1`，仅在探测失败时才追加 `-I`（SDK 原生 clang 自带 libcxx-ohos，无需追加） |
| 3 | `error: unknown rune table for this platform` | OHOS libc++ 需显式声明 rune table 提供方 | 添加 `-D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE`（两种工具链环境都需要） |
| 4 | CI 上 `error: redefinition of 'strtoll_l' / 'strtoull_l'`（来自 `libcxx-ohos/include/c++/v1/__support/musl/xlocale.h`） | 配方按本地 DevEco libc++ 的情况**无条件** force-include `locale_stub.h`；但 SDK 原生 clang 用的 libcxx-ohos 在 `__support/musl/xlocale.h` 里**已经**定义了这两个函数，于是撞车 | 改为编译探测：`<cstdlib>+<locale>+strtoll_l(...)` 探针通过就不注入 shim，只有探针失败（DevEco libc++）才生成并 `-include locale_stub.h`。同一个配方在 CI 与本地都能过 |
| 5 | `-D_LIBCPP_HAS_NO_LOCALIZATION` 导致 iostream/locale 被禁用 | 该宏过于激进，rapidfuzz 需要 `<locale>` / `<iostream>` | 不使用该宏（见 #4） |
| 6 | 路径含空格（`DevEco Studio`）导致 CMake split | `CMAKE_CXX_FLAGS` 字符串被 CMake 按空格 split | 探测得到的 include 路径在写入 `CXXFLAGS` 时转义空格（`DevEco\\ Studio`）；CI 上根本不会走到这条分支 |
| 7 | taskflow `find_package(Taskflow 3.9.0)` 会命中 conan taskflow/4.1.0 但 target 名大小写不符（`Taskflow::taskflow` vs rapidfuzz 需要的 `Taskflow::Taskflow`） | conan taskflow 的 cmake_target_name 为小写 | 不依赖 conan taskflow，让上游走 `add_subdirectory(extern/taskflow)` 使用 vendored 版本 |
| 8 | `test_utils` 断言 `default_process("  Hello, World!  ") == "hello world"` 失败（实得 `'hello  world'`） | `default_process` 只去首尾空白、转小写、去标点，**保留内部空白**；期望值写错 | 断言改为 `'hello  world'`，并补一条「内部空白保留」的正向断言。同时收紧 E212 回退：仅当动态加载器明确拒绝（`Permission denied` / `cannot open shared object file`）才降级为 ELF 静态校验，其它异常一律让测试变红 |
| 9 | CI #62695 `Error in source() method, line 67` / `ConanConnectionError: Read timed out`，3 次尝试分别停在 307KB / 3.7MB / 3.7MB（均为 57.9MB 的 4%~6%） | worker 到 `files.pythonhosted.org` 的链路中途停顿；conan `get()` 默认 `retry=2` 只有 3 次机会，全部耗尽。CI 的 mirror 预下载也救不了：worker 上没有 `curl`（`[Errno 2] No such file or directory: 'curl'`），且该 host 无已配置镜像 | `source()` 放宽重试预算为 `retry=6, retry_wait=15`（同 openfast/5.0.0 写法）。属网络/基础设施问题，非配方缺陷 |
| 10 | CI #62781 `Error in source() method, line 72` / `sha256 hash failed`（Provided `b0ba1ccc...` / Computed `400d0b53...`），仅 33s 就失败 | 曾把 `conandata.yml` 的 URL 从 PyPI sdist 换成 GitHub tag 归档 `github.com/rapidfuzz/RapidFuzz/archive/refs/tags/v3.12.2.tar.gz`，**却沿用 sdist 的 sha256**。二者是不同的产物：归档实测 sha256 = `400d0b53ce27a11e5896dfe139429b78a74562d8e0c16999b7f0bd58f521c14a`；且归档里 0 个 `.cxx`（Cython 未预生成），`extern/rapidfuzz-cpp`、`extern/taskflow` 是空 submodule。即使把 sha256 改成归档的值，CMake 构建仍不可用 | URL 恢复为 PyPI sdist + 正确的 `b0ba1ccc...`，并在 `conandata.yml` 写明「不得替换为 GitHub 归档」的原因，防止再次误改 |
| 11 | 探测逻辑被改成「探针 1 用完整链接」并在 `_libcxx_include_dir()` 里加 `ohos-sdk` / `/data/service/hnp/` 路径白名单 | 探针 1 的问题是「驱动能否找到并解析 C++ 头」，与链接无关；用链接判定会因无关原因（搜索路径上还没有 libc++abi）失败，从而走进错误分支。路径白名单又把 CI 的宿主布局写死进配方，本地 WSL 的 DevEco 路径会被判为非法 → 直接 `ConanException` | 探针恢复 `-fsyntax-only`；`_libcxx_include_dir()` 去掉路径白名单，保持工具链无关（与 #4 的结论一致） |
| 12 | CI #62787 `CMake Error: The source directory /extern/taskflow does not contain a CMakeLists.txt file` | 仍在使用 GitHub tag 归档（或 sha256 不匹配导致回退到旧配方），该归档不含 submodule 内容，CMake 找不到 vendored `taskflow` 与 `rapidfuzz-cpp` 的 CMakeLists.txt | 同 #10：强制使用 PyPI sdist（已含所有 submodule 内容），在 `conandata.yml` 写明禁止替换 |
| 13 | CI #62819（CI-016）/ #62860（CI-011）`conan create TIMED OUT after 3600s`，两个**不同** worker 都在 `source()` 下载阶段被 KILL，日志显示下到 93%（54.3MB / 57.9MB） | **#9 的结论错了**：这不是"偶发网络抖动 + 重试预算不够"，而是到 `files.pythonhosted.org` 的**稳态带宽**就只有 ~10-15KB/s（实测 10355 B/s）。57907839 / 10355 ≈ **5592s**，即使零失败也必然超过 `DEFAULT_BUILD_TIMEOUT=3600s`，所以调大 `retry` 永远救不回来。两条放大因素让 CI 的两道保险同时失效：(a) `build_and_test.sh` 的 `get_mirrors()` 对 `files.pythonhosted.org` 显式 `return [url]`（注释："conandata.yml 不太可能引用这里"），镜像注入对本 host 是空操作；(b) pre-download 需要 `curl`，worker 上没有（`[Errno 2]`），直接跳过 | `conandata.yml` 的 `url` 改为**有序 URL 列表**：TUNA / 阿里 / 华为 / 腾讯四个国内 PyPI 镜像在前（实测 28 / 18 / 10 / 2.2 MB/s），官方站留最后兜底；四者下载后 sha256 实测均为 `b0ba1ccc...`，与官方**逐字节一致**，故复用同一 sha256（R37 换 host 语义等价）。官方条目用带内容哈希的规范路径 `/packages/<xx>/<yy>/<hash>/<file>`，不用旧的 `/packages/source/...` 跳转形式（镜像只镜像前者，TUNA 对旧形式 404）。`retry=6/retry_wait=15` 保留为镜像链路的兜底。同 `astlib/0.13.2`（PR #7425 #36249 同 host 同故障） |
| 14 | 评审（MR 13140）rule4 FAIL：上游 129 个测试函数一条没跑，PR 描述还少报成「上游用例数 8 / 通过率 0/0」 | 上游 pytest 既没进 `build()` 也没进 `test_package`：`tests/` 只存在于 sdist 里，CI 全程触不到；PR 描述按「测试文件数」填了 8，与评审按 `grep -c '^\s*def test_'` 统计的 **129** 对不上 | 把 sdist 的 `tests/` **逐字** vendor 进 `test_package/tests/`（23 个 `.py`），`test()` 用 conan python/3.12.9 真实执行 `python3.12 -m pytest tests/ -q`，解析 pytest 自己的汇总行输出 `HMBS_UPSTREAM_TEST_RESULT`（数字只来自命令输出）。同时 `requires("numpy/2.5.2")`（制品仓已发布，contourpy/1.2.1 同款裸引用）让 16 项 numpy 用例真正执行；`pytest`/`hypothesis` 经 `pip install --target` + `PYTHONPATH` 注入 conan python（`test_hypothesis.py` 顶层 `import hypothesis`，缺了无法收集）；pandas 制品仓无包，尽力安装否则 2 项按上游 `importorskip` 跳过并如实计数。PR 描述改为实测的 **129** 与 CI 实测通过率 |
| 15 | CI #63465 上游 pytest 收集期 16 个模块全部 `ImportError: Error relocating .../fuzz_cpp...so: PyModuleDef_Init: symbol not found` | 上游 CMakeLists 只 `find_package(Python COMPONENTS Interpreter Development.Module)`，扩展模块不链接 libpython，符号留给解释器进程导出。但 conan `python/3.12.9` 的解释器**不导出** libpython 符号（CPython 自己的 `lib-dynload/*.so` 是显式链接 `libpython3.12.so` 的，见 python 配方注释），于是 5 个扩展全部无法 dlopen。而 `import rapidfuzz` 在扩展载入失败时**静默回退**到 `*_py` 实现，所以消费者测试一直"通过"，从未真正验证 C 扩展 | ① 主配方给 CMake 追加 `-DCMAKE_MODULE_LINKER_FLAGS=<libpython3.12.so>`，让扩展记录 `DT_NEEDED`，不再依赖解释器导出符号；② `package()` 末尾按 python 配方同款流程自签 `.so`；③ test_package 增加 C 扩展硬门禁（直接 import 5 个 `*_cpp` 模块，无纯 Python 兜底，失败即红，仅真 E212 才回退）；④ 消费者测试新增 `fuzz.ratio.__module__` 含 `_cpp` 断言，杜绝再退化成纯 Python 却报绿 |
| 16 | pandas 装得上却 import 失败：`ImportError: Error relocating .../lib-dynload/_ctypes...so: ffi_prep_closure_loc: symbol not found` → `test_process.py` 的 2 项 `pd.NA` 用例只能 `importorskip` 跳过 | 与本包无关：`<py>/lib/python3.12/lib-dynload/_ctypes*.so` 是 conan `python/3.12.9` 运行时自带的，它要的 `ffi_prep_closure_loc`（libffi ≥ 3.4 才有）在 worker 上解析不到。已排除「libffi 不在搜索路径」这一可能：test_package 显式 `requires("libffi/3.5.2")` 后其 `lib/` 确实出现在 LD_LIBRARY_PATH（CI #63492 实测路径 `.../p/libff7862779dad895/p/lib`），CI #63492 仍复现同一错误，故根因在 python 配方侧的 _ctypes/libffi 组合，不在本适配范围 | 保留 `requires("libffi/3.5.2")`（无害且为后续修复留好路径）。当前按**上游自身设计**由 `pytest.importorskip("pandas")` 跳过 2 项，并在 `HMBS_UPSTREAM_TEST_RESULT.note` 与 PR 描述中如实写明具体技术原因与定位结论，不做任何掩盖。若日后要 0 skip，需在 python/3.12.9 配方侧修 _ctypes 与 libffi 的符号匹配 |

> 注：CI #62504 的自动诊断把失败标为「网络问题 / 源码下载超时」，但该次构建的 `Read timed out` 已被 conan 重试救回，**真实**失败是 #4 的 `redefinition of 'strtoll_l'`。#62695 是真正的下载失败。读 CI 报告时以「失败步骤完整日志」末尾为准。
>
> 注 2：#62819/#62860 的 CI 报告把超时归类为「环境问题 / 建议重试」。按上面的 #13，这个归类是错的 —— 带宽是稳态的，重试不会改变结果。**判断超时是"抖动"还是"稳态带宽不足"的口径**：拿 `content-length` 除以日志里实际下载耗时，若商大于 `DEFAULT_BUILD_TIMEOUT` 就是稳态不足，必须换源，调重试无效。

## 依赖版本
- python/3.12.9 (Conan, OHOS aarch64)
- vendored: rapidfuzz-cpp 3.2.0, taskflow 3.9.0

## 验证结果
- 构建产物: 5 个 CPython 扩展模块（fuzz_cpp / utils_cpp / process_cpp_impl / metrics_cpp / _initialize_cpp）
- 消费者 test_package: fuzz/distance/process/utils 共 16 项断言全部通过（含 C 扩展来源断言），CI #63492 实测 `fuzz.ratio from rapidfuzz.fuzz_cpp`
- 上游测试: `test_package/tests/` 为 sdist `tests/` 逐字副本（18 个测试文件 / **129** 个 `def test_` / pytest **386** 个用例项），由 `test()` 用 conan python/3.12.9 真实执行并输出 `HMBS_UPSTREAM_TEST_RESULT`
- CI #63492（head `73a3e736`）实测: **384 passed / 0 failed / 2 skipped / 0 errors（discovered 386）**，30.52s；L0/L1 全 pass，L1c 已识别上游官方测试。2 项 skip 为 pandas 门控用例，原因见 #16

## 注意事项
- 不设置 `CMAKE_SYSTEM_NAME` 是关键：FindPython 需要运行解释器。若未来 CMake 版本改变此行为，需改用 `Python_FIND_VERSION` 显式指定版本。
- `extern/taskflow` 与 `extern/rapidfuzz-cpp` 为上游 vendored 版本，未使用 conan 包（避免 target 名/版本冲突）。
- CI 环境下 test_package 可能遇 E212（hmmac 安全标签拒绝 dlopen 用户路径 .so），已内置 ELF 静态校验回退；该回退只作用于消费者测试，**上游 pytest 走真实 import，失败即失败**（CI #63044 实测未触发 E212，live import 成功）。

---

**编译结束**: 2026-09-27
**最终状态**: built (CI #62819/#62860 源码下载超时已修 — conandata.yml 改国内 PyPI 镜像有序列表，notes #13)
