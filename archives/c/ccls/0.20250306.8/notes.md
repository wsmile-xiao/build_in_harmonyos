# ccls 0.20250306.8 鸿蒙 PC (aarch64) 适配笔记

## 概述

ccls 是 C/C++/Objective-C 语言服务器（LSP），C++17 + CMake 工程，依赖 LLVM/clang 库。
源码 = 上游 master commit `66481f7b1eb1cf4d1edc12442e275a4efe286850`（上游无 0.20250306.8 tag，
版本号按用户要求保持 0.20250306.8）。产物为命令行可执行文件 `bin/ccls`（R38 tool 类型，需 commands.json）。

## 编译环境

- 构建系统: cmake（`find_package(Clang REQUIRED)` + `find_package(RapidJSON)` + `find_package(Threads)`）
- 编译器: `/data/service/hnp/bin/clang` / `clang++`（clang 15.0.4 系统工具链，原生构建）
- C++ 标准: C++17（CMakeLists 强制）
- 编译日期: 2026-08-25
- 状态: built（conan-verify 通过，未 upload）

## 依赖（ohpcd 制品仓已发布）

| 依赖 | 版本 | 用途 |
|------|------|------|
| clang | 22.1.8 | libclang-cpp.so + libLLVM.so + include + LLVM/Clang CMake config（RTTI 开） |
| rapidjson | 1.1.0 | header-only JSON（USE_SYSTEM_RAPIDJSON=ON 时 find_package(RapidJSON)） |

## 编译步骤

```bash
# 1) conan 装依赖 + 生成工具链（探索阶段用 CMakeDeps+CMakeToolchain 取依赖；正式 recipe 只用 CMakeToolchain）
conan install <deps> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 2) 手动 configure（关键：CMAKE_PREFIX_PATH 指向 clang/rapidjson 包目录，勿用 CMakeDeps 生成的 ClangConfig）
cmake -B build -S . \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ \
  -DCMAKE_CXX_FLAGS=-stdlib=libc++ \
  -DCMAKE_EXE_LINKER_FLAGS=-stdlib=libc++ \
  -DUSE_SYSTEM_RAPIDJSON=ON \
  -DCMAKE_PREFIX_PATH="<clang_pkg>;<rapidjson_pkg>" \
  -DRapidJSON_INCLUDE_DIRS="<rapidjson_pkg>/include" \
  -DCCLS_VERSION=0.20250306.8

# 3) 编译 + 安装
make -C build -j2 && cmake --install build --prefix "$TEST_PREFIX"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(Clang)` 只找到 `clang::clang`，链接 `clangIndex/clangFormat/...` 报 target 不存在 | conan_toolchain 把 CMakeDeps 输出目录 prepend 到 CMAKE_PREFIX_PATH，CMakeDeps 生成的 ClangConfig 遮蔽了 clang 包自带的 LLVM ClangConfig（后者才定义 clangIndex 等目标 + CLANG_LINK_CLANG_DYLIB=ON） | recipe 只用 CMakeToolchain（不用 CMakeDeps），generate() 里显式 `CMAKE_PREFIX_PATH=<clang包>;<rapidjson包>`，`find_package(Clang)` 命中包内 `lib/cmake/clang/ClangConfig.cmake` |
| 2 | rapidjson include 未生效 | ccls CMakeLists 用 `RapidJSON_INCLUDE_DIRS` 变量，rapidjson 包自带 config 只设 `RapidJSON_INCLUDE_DIR` | generate() 显式传 `RapidJSON_INCLUDE_DIRS=<rapidjson_pkg>/include` |
| 3 | `ccls --version` 显示 `<unknown>` | 导出源码无 `.git`，CMake `git describe` 失败 | configure 传 `-DCCLS_VERSION=0.20250306.8` |
| 4 | 上游 index_tests 全部无法运行 | test.cc 硬性要求 clang 23.0.0git（`kRequiredClangVersion`），本包 clang 22.1.8 → `Index tests must be run using clang version 23.0.0git` | 记录为平台/依赖限制；test_package 用 `--version`/`--help` 做真实冒烟测试 |

## 源码修改

无（首次适配未改源码，无补丁；`refresh-patch --auto` 无可生成项）。

## 验证结果

```bash
$ ccls --version
ccls version 0.20250306.8
clang version 22.1.8
$ ccls --help    # OVERVIEW: C/C++/Objective-C language server ... exit 0
$ ccls --test-index=   # -> Index tests must be run using clang version 23.0.0git（上游版本门槛，非本包缺陷）
```

## 注意事项

- ccls 二进制运行时 NEEDED `libclang-cpp.so.22.1` / `libLLVM.so.22.1` / `libc++_shared.so`，由 conan 依赖 clang/22.1.8 提供（VirtualRunEnv/conanrun 自动注入 LD_LIBRARY_PATH）。
- 运行时 resource dir 由编译期 `clang -print-resource-dir` 烘焙进二进制（CMAKE_PREFIX_PATH 含 clang 包 → 指向 clang 包 `lib/clang/22`）。
- OHOS 上 clang 依赖包需代码签名（clang 配方已处理）；ccls 本机实测可直跑（当前环境未拦截）。
---

**编译结束**: 2026-08-25 17:21
**最终状态**: built

---

## 主编打回修复记录（2026-08-25）

### 1. conandata.yml: file:// → https（致命项修复）

- 原 `sources.url` 为本地 `file://.../.build-cache/predl_cache/...`（由 CI `build_and_test.sh`
  的 pre-download 机制改写残留，远端 CI 无法访问 → conan create 必失败）。
- 已改为 `https://codeload.github.com/MaskRay/ccls/tar.gz/66481f7b1eb1cf4d1edc12442e275a4efe286850`，
  sha256 保持 `245958b063772455c5273711bdbc15092554f7836245c48577b901cfb9f594e8`。
- **验证**：清空 conan 缓存后重跑 `conan-verify` G2（conan create），实测日志
  `reports/conan-create.log`：
  `Sources correctly downloaded from https://codeload.github.com/...` → `Building from source`
  → `Package ... created` → test_package `--version/--help OK`。
- 注：codeload URL 含 `github.com`，conan-verify 的 E017 镜像注入逻辑
  `replace("https://github.com", ...)` 对 `https://codeload.github.com` 是**无操作**
  （字面子串不匹配），不会误注入 ghfast.top（实测 ghfast.top 对该路径 403）。
- 注：CI `build_and_test.sh` 的 pre-download 步骤会在每次 W3/CI 运行时把 conandata.yml
  改写回 `file://predl_cache`（且不恢复），因此**每次 finish/W3 后必须手动恢复 https URL**
  再提交，否则致命项复发。

### 2. 知识草稿 E335 → E2162（撞号修复）

- 原草稿 `knowledge/drafts/E335-draft-30A0.{kv,md}` 撞号（E335 已被
  `E335-draft-MLTN`、`DRAFT-E335-libselinux-monorepo-subdir` 等占用）。
- 已改名 `knowledge/drafts/E2162-draft-30A0.{kv,md}`（E2162 为草稿目录最大编号 E2161 之后
  的下一个可用编号，已确认 drafts/graph/index.tsv 均无 E2162 占用），内部 `id: E2162`、
  `doc_file: doc/E2162.md`、md 标题同步改为 E2162。manifest.yaml 的 `knowledge_ref: [E2162]`
  已同步指向新编号。

### 3. conan-verify 8 门禁：G4/L2/L4/L5「跳过」根因与处理

- **根因（framework 只读，未改动）**：`conan_verify.py` 的 G4 用
  `conan list <ref>:* --format=json` 取 package_id，按旧版 Conan（<2.11）嵌套结构解析
  `listing["Local Cache"][software][ref]`；当前 OHOS 适配版 **conan 2.29.1** 的 JSON 已扁平化
  （`Local Cache` 直接以 ref 为键，无 software 层），实测 `KeyError 'ccls'` → G4 报
  `无法找到程序包 ID` → `_cache_path` 未赋值 → L2/L4/L5 全部「跳过（无 cache 路径）」。
  另：G2 的 package_id 正则 `\w+/\w+@\w+/\w+` 不匹配带点版本号 `0.20250306.8`；工具 L2
  裸环境执行二进制不注入 clang 包 `LD_LIBRARY_PATH`，对本包必然失败（实测 rc=141）。
- **处理**：按 SKILL 失败处理路径，在 `reports/conan-verify-report.md` 追加「附注(A)」，
  记录工具受限根因 + 等价真实执行证据：G4 产物清单；L2 `--version/--help`（注入 clang
  lib LD_LIBRARY_PATH，rc=0）；L4 `readelf`：DYN→PIE enabled、GNU_STACK RW→NX enabled、
  BIND_NOW→RELRO full、canary 未找到（非阻断）；L5 sha256 基线
  `bin/ccls=eec89c512ce6...`、`licenses/LICENSE=c71d239d...`。G0-G3 为工具真实 PASS。
- **其余门禁实测**：G0 PASS（E092 已处理）、G1 PASS、G2 PASS（https 真实下载构建）、
  G3 PASS（无 lib/ 纯可执行包）。W3 本地 CI：JUNK_PR_DIFF 作用域 `archives/c/ccls/` +
  knowledge/drafts/E2162 后 `JC_RESULT=pass`，L0/L1/L4/L5 pass，L2 skip 为 CI 对
  clang 动态链接二进制的非阻断告警。

### 4. test_package/conanfile.py bash 路径（中）

- `bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")`
  → `bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"`
  （与 archives/a/at-spi2-core/2.60.5 一致），避免 CI 缺 CONFIG_SHELL 时硬编码路径失败。
- 实测 test_package 通过（本机 `shutil.which("bash")` → `/storage/Users/currentUser/usr/local/bin/bash`）。

### 5. manifest.yaml（中）

- 补充 `compile_date: "2026-08-25"`、`test_results: {type: manual, total: 2, passed: 2,
  failed: 0}`（上游 index_tests 硬性要求 clang 23.0.0git，clang 22.1.8 下被主动拒绝；
  以 test_package 真实冒烟 --version/--help 2/2 替代）、`knowledge_ref: [E2162]`。

### 6. finish 复跑结果

- `finish ccls 0.20250306.8 built` 通过（exit 0）。W3 首跑因全仓 tracked junk 误伤
  （`archives/i/isa-l_crypto/2.26/conandata.yml.orig`、
  `archives/m/middleclass/4.1.1/conandata.yml.ghfast-bak`、
  `archives/s/swift-corelibs-blocksruntime/6.3.3/.staging-verified`，均 origin/main 存量，
  非本 PR 引入）在 full 模式被拦；用 `JUNK_PR_DIFF=.tmp-ccls/pr-ccls.diff`
  （作用域仅 ccls 8 文件 + knowledge/drafts/E2162 2 文件，10 文件）复跑，`JC_RESULT=pass`。
- 每次 conan-verify/W3 会残留 `conandata.yml.ghfast-bak`（工具 E017 流程写 bak 不清理），
  已删除；下次 run 前若再现同样清理。conandata.yml 的 https URL 为最终提交版本。
