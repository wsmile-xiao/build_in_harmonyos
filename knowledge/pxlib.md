# pxlib 0.6.9 适配知识扩展（主动召回）

> 生成时间：2026-09-19；分支：feat/pxlib-0.6.9；仓库：build_in_harmonyos
> 本文件按 SelfWorkflow「主动获取相关知识扩展」模块要求，由 openharmony-knowledge-recall 流程召回。

## 1. 检索键清单

| 键 | 值 |
| --- | --- |
| 库名 / 领域词 | pxlib、paradox、C 库、CMake+autotools |
| 构建系统类型 | CMake（add_library SHARED，无 find_package 外部依赖）+ autotools（configure 已预生成） |
| 阶段 | W0 依赖分析 → 配方编写 → 交叉编译 |
| 报错原文 | （暂无，首次适配） |

## 2. 知识源同步与图谱检索

- `git fetch origin main && git pull origin main --ff-only`：Already up to date（knowledge/ 与 main 一致）。
- 图谱引擎：skill 目录中 `scripts/ohc-run.py` 不存在（脚本缺失），改为直接检索 `knowledge/graph/*.kv`。
- `grep -ril "pxlib\|paradox" knowledge/`：**未命中任何条目**（E 编号无 pxlib 专项条目）。

## 3. 同类库归档（可复用结论）

检索 `archives/c/`，找到与 pxlib 同类型（Paradox/老式 C 文档解析库）的 **catdoc 1.0.0** 已适配归档：

### 3.1 catdoc 1.0.0 经验（archives/c/catdoc/1.0.0/notes.md）

- 构建：Autoconf + 手写 Makefile.in；`conan create archives/c/catdoc/1.0.0 -pr:h ohos-aarch64 -pr:b default --build=missing`。
- **R8（clang-15 优化 bug）**：老式 C 代码（1994 年来源）在 `-O1` 及以上优化级别生成错误代码，`main()` 前 SIGSEGV；逐文件二分定位到 fileutil.c。修复：`tc.extra_cflags = ["-O0"]` + 修补 configure 中的 `-O2`。
  → **pxlib 警示**：pxlib 源码同样老旧（1999–2004 年代码），若交叉编译后运行期崩溃且 `-O0` 正常，优先怀疑 clang 优化 bug，用 `-O0` 二分定位。
- **R9（旧式 C 警告）**：大量隐式函数声明/隐式 int/类型不匹配，用 `-Wno-error-*` 抑制；pxlib 的 CMakeLists 带 `-Wall -Wpointer-arith -W`，注意 `-W` 会把更多警告升级为错误信号，但 conan 侧不会加 `-Werror`，警告不阻塞。
- 安装：`--prefix=/` + installroot 模式；pxlib 用 CMake `CMAKE_INSTALL_PREFIX` 控制即可。

### 3.2 其它相关归档

- `archives/c/` 下无 pxlib 目录（首次适配）。

## 4. operations 文档复用结论

来源：`knowledge/operations/*.md`（build-systems.md / harmonyos-specifics.md / packaging.md / dependency-resolution.md）

- OHOS aarch64 profile：`~/.conan2/profiles/ohos-aarch64`（已配置，conan 2.29.1，remote ohpcd 匿名可读）。
- CMake 库标准配方骨架：`toolchain = "cmake"`，`generate()` 写 `CMakeToolchain` + `CMakeDeps`，`layout()` 用 `cmake_layout`；`layout` 后需修正 `self.cpp_info` 头文件路径指向 `build/Release` 下的 `include/`。
- pxlib 的 CMakeLists 用 `configure_file` 在 `CMAKE_BINARY_DIR` 生成 `paradox.h`/`paradox-gsf.h`/`pxversion.h`（模板在 `include/*.h.in`）。~~安装时 `CMakeLists` 尾部（截断未读）会把它们装到 `include/`~~（**已证伪**：上游 CMakeLists.txt 无 `install()` 规则，`cmake.install()` 无产物；最终方案为 `package()` 手动 `copy()` 生成头进 `package_folder/include`）。
- iconv：OHOS musl libc 自带 `iconv.h`/`iconv()`，无需外部 conan 包（系统库）。
- libgsf-1：可选（`ENABLE_GSF=OFF`，默认 OFF），不引入、不声明。

## 5. 横向扫描同类 PR

- 目标仓库历史 PR/Issue 中未发现 pxlib 相关适配（grep 无命中）；catdoc 归档证明「老式 C 解析库 + OHOS」路径可行。

## 6. 结论（写入后续适配阶段）

1. pxlib 无强制第三方 conan 依赖（仅 iconv 系统库），W0 下载核验步骤 N/A，可直接进入目标库适配。
2. 采用 CMake 构建（源码已带 CMakeLists.txt，3.12+，比 autotools 路径更省事）。
3. 风险清单：
   - R1 版本宏漂移：CMakeLists 写死 `0.6.8`（`PXLIB_MICRO_VERSION "8"`），与 0.6.9 tag 不一致 → 配方 `CMAKE_ARGS` 或源码 patch 修正到 0.6.9（上游 release tarball 自身缺陷，patch 记录为已知上游不一致）。
   - R2 生成头路径：`paradox.h`/`paradox-gsf.h`/`pxversion.h` 是 build 期 `configure_file` 产物，consumer 侧头目录必须含 `CMAKE_BINARY_DIR/include` 的安装结果（**已证实**：无 install 规则，需 `package()` 手动拷贝）。
   - R3 老式 C 代码 + clang 优化：若链接/运行异常，按 catdoc R8 用 `-O0` 二分。
   - R4 `add_library(pxlib SHARED)` 未设 `OUTPUT_NAME`，产物为 `libpxlib.so`，consumer 侧 `requires("pxlib/...")` 链接名 `pxlib`。
4. 上游测试入口：`CMakeLists.txt` 无 `enable_testing()`/`add_test()`，`Makefile.am` 无 `TESTS=`，仓库无 `tests/` 目录 → **上游无自动化测试入口**，需如实汇报「无测试入口」并以 test_package + `px_read_document` 冒烟（构造最小 Paradox 文件）替代。
