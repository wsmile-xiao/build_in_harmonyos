# tlsh 5.0.0 适配笔记

## 编译环境

- 构建系统: cmake（上游根 `CMakeLists.txt`，`project(TLSH)`）
- 编译日期: 2026-09-17
- 编译器: clang / clang++ 15.0.4（OHOS SDK，`/data/service/hnp/bin`）
- Conan: 2.29.1 + `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, build_type=Release）
- 状态: built（本机 conan-verify 通过；尚未经 release 流水线 upload，故不标 published）

## 编译步骤

```bash
conan create archives/t/tlsh/5.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方内部（`conanfile.py`）：

1. `source()`：`get(**conan_data["sources"], strip_root=True)`
2. `generate()`：`CMakeToolchain` 注入 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4 兼容）
   与 `-DTLSH_SHARED_LIBRARY=0/1`（映射 `shared` 选项）
3. `build()`：`apply_conandata_patches()` → `cmake.configure()` → `cmake.build()`
   → 补 `bin/tlsh` 符号链接 → `cmake.test()`（ctest）
   → `sh Testing/test_parts.sh` → `sh Testing/test_pattern.sh`
4. `package()`：`cmake.install()`
5. `package_info()`：`libs=["tlsh"]`、`defines=["BUCKETS_128"]`、`bindirs=["bin"]`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 拒绝 `cmake_minimum_required(VERSION 2.6)` | CMake 4.x 移除了对 <3.5 的兼容 | 配方 `generate()` 用 `cache_variables` 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。**必须走 cache_variables（-D 命令行）**：`tc.variables` 写进 `conan_toolchain.cmake`，加载时机在项目 `cmake_minimum_required` 之后，设了不生效。不改上游源码，故不产生补丁 |
| 2 | ctest 一启动就以 127 失败（`error: (127), you must compile ../bin/tlsh`） | 上游把 `bin/tlsh -> tlsh_unittest` 符号链接放在 `install(CODE file(CREATE_LINK ...))` 里，**构建树里没有**；而 `Testing/test.sh` 默认就用 `../bin/tlsh`（上游注释：issue #115 - CREATE_LINK does not work on CENTOS 7） | `build()` 内 `cmake.build()` 之后按上游 `make.sh` 的同一动作补链接（只落在 conan 构建目录的生成目录 `bin/`，不进提交面） |
| 3 | `tlsh -split 50,100,200 -f Week3.txt` 段错误（rc=139），上游 test 9 失败 | **上游真实缺陷**：`src/input_desc.cpp` 的 `inputd->tptr` 由 `malloc` 分配，随后只在分发循环里 `tptr[ti]=NULL`，而 `splitlines` 分支第一轮就 `ti = n_file` 短路该循环 → 超出「实际命中分隔位置数」的槽位保持未初始化堆内容，输出循环仍按 `n_file` 遍历并解引用。glibc 上新页为 0 时侥幸通过（上游 exp 夹具正是 3 行），OHOS 上必现 | `patches/0001-src-input_desc.cpp.patch`（bugfix，+7 行）：分配后显式把 `tptr[0..max_files]` 全部置 NULL |
| 4 | 消费者编译期 `TLSH_STRING_LEN_REQ` 未定义 | 上游用 `add_definitions(-DBUCKETS_128)`，该宏只作用于库自身编译；它同时决定公共头文件里的 `TLSH_STRING_LEN_REQ` 与 `getHash()` 默认参数签名 | `package_info()` 导出 `self.cpp_info.defines = ["BUCKETS_128"]` |
| 5 | test_package 里 `tlsh -version` command not found | 静态库依赖的 `require.run` 默认为 False，`VirtualRunEnv` 不把该包的 `bindirs` 注入 `PATH` | test_package 用 `self.requires(self.tested_reference_str, run=True)`，并声明 `VirtualRunEnv` 生成器 |
| 6 | `lang-preflight` 判 `python` → `env_unsupported` | 工具把 `py_ext/setup.py`（**独立 PyPI Python 绑定模块**的打包 manifest）当成主体 manifest（`notes/defects/knowledge-and-scan.md` 同族 clib/cube2font 误判） | 按该条绕行：排除绑定/辅助目录（`py_ext/`、`java/`、`js_ext/`、`tlshCluster/`、`register/`、`Windows/`、`docs/`）重跑，得 `detected=cpp, build_system=cmake, cpp 占比 100%`；原始误判与重跑输出均留档 |

## 源码修改

`patches/0001-src-input_desc.cpp.patch`（`patch_type: bugfix`，平台无关）：

```diff
 	inputd->tptr = (Tlsh **) malloc ( sizeof(Tlsh *) * (inputd->max_files+1) );
+	// The loop below only nulls tptr[0] before the splitlines branch
+	// short-circuits it (ti = n_file), so any slot beyond the number of
+	// split positions actually found would keep uninitialized heap
+	// contents and be dereferenced by the output loop.
+	for (int ti=0; ti<inputd->max_files+1; ti++) {
+		inputd->tptr[ti] = NULL;
+	}
```

补丁由 `refresh-patch --auto` 从编辑追踪器生成（`src/input_desc.cpp` 单文件，+7/-0）。

## 依赖版本

无第三方依赖。上游根 `CMakeLists.txt` 只有 `find_package(Threads REQUIRED)`，
`src/*.cpp` 的 include 全为 C/C++ 标准库与项目内头文件 → **W0 依赖清单 = none**。

## 验证结果

```bash
# 1) 上游测试（配方 build() 内真实执行；干净轮日志与计数见 reports/）
conan create archives/t/tlsh/5.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#   → ctest: 100% tests passed, 0 tests failed out of 1
#   → Testing/test_parts.sh: passed
#   → Testing/test_pattern.sh: passed（TAB/COMMA 各 2 个编号测试块）
#   → test_package: checks=16 failed=0；安装后 CLI `tlsh -version` 自报 5.0.0

# 2) 复现原始缺陷（未打补丁时）
../bin/tlsh -split 50,100,200 -f example_data/Week3.txt -o <out>    # → Segmentation fault (rc=139)
# 打补丁后同一命令输出 3 行，与上游夹具 exp/example_data.Week3.split.tlsh 逐字一致：
diff --ignore-all-space tmp/example_data.Week3.split.tlsh exp/example_data.Week3.split.tlsh   # → 无差异

# 3) 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight tlsh 5.0.0 --src <排除绑定/辅助目录后的源码树>
#   → detected=cpp, build_system=cmake, cpp 占比 100%
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libtlsh.a` | TLSH 静态库（上游默认形态；`TLSH_SHARED_LIBRARY=0`） |
| `include/tlsh/tlsh.h`、`include/tlsh/tlsh_version.h` | 公共头文件（后者由上游 CMake 生成版本宏） |
| `bin/tlsh` | 命令行工具（上游 `bin/tlsh_unittest` 的符号链接，与上游 install 一致） |

## 注意事项

- **`shared` 选项**：默认 `False`，与上游默认一致（`src/CMakeLists.txt` 注释明确"库很小、没有必要做共享库"）。共享形态下上游测试目标带 `SKIP_BUILD_RPATH`，配方在该形态下以 `LD_LIBRARY_PATH=<源码>/lib` 直接执行同一条上游脚本（静态默认形态走 ctest）。
- **语言绑定不在本包范围**：`py_ext/`（PyPI Python 模块）、`java/`（Gradle）、`js_ext/`（JS 移植）都不是 CMake 目标，属独立分发；`Testing/python_test.sh` 需要先构建 `py_ext` 模块，故计为 NOT_RUN（见 `reports/test-report.md`）。
- `tlsh_parts` / `tlsh_pattern` / `simple_unittest` / `timing_unittest` / `order_bug` 只构建不安装（上游 `install()` 只装 `tlsh_unittest` 及其 `tlsh` 链接）。
- 上游 5.0.0 的 digest 默认带 `T1` 前缀（`Change_History.md`），消费者断言按该口径写。
- CMake 4 兼容项与 `BUCKETS_128` 导出两项都与知识库既有条目同族（`DRAFT-E321-cmake4-policy-version-minimum`），本次未新建草稿。
