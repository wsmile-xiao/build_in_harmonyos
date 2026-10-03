# mtxclient 0.10.1 — HarmonyOS PC 适配笔记

> 创建时间: 2026-09-29
> 分支: feat/mtxclient-0.10.1
> 当前状态: 🟡 built（配方/补丁/test_package + 本机门禁全部通过；W0 依赖全部已发布；设备 conan create 待空闲窗口）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | mtxclient（Matrix 客户端-服务器 API 库，Nheko 使用） |
| 版本 | 0.10.1（2025-08-02 上游发布） |
| 构建系统 | CMake（另有 meson.build，本配方不使用） |
| 语言标准 | **C++20**（必需，见 §三.1） |
| 源码 | https://github.com/Nheko-Reborn/mtxclient/archive/refs/tags/v0.10.1.tar.gz |
| sha256 | 203be46a08e1dc6cfc068d0911f3b09976f48e4cc4302c3517b9c0f4e53631e3 |
| 产物 | libmatrix_client.so.0.10.1 + include/mtx/** + include/mtxclient/** + lib/cmake/MatrixClient/** |

## 二、W0 依赖发布检查（R36）—— 通过

### ⚠️ 先说方法学：退出码不可信

本次会话最初用 `conan download <ref> -r=ohpcd --only-recipe` 的**退出码**判断依赖是否已发布，
得出了「coeurl 未发布」的**错误结论**。实际复测发现：

- `conan download coeurl/0.3.2` 会打印 `packages: No packages found for this revision`
  却仍然 **exit 0**；
- 同一 ref 在不同时刻会返回 `error:system acceleration policy not enabled`（瞬时抖动）。

因此**退出码和输出文本都不能作为"是否已发布"的判据**。R35 的正确落地方式是用
`conan graph info` / `conan install` 读节点的 `binary` 字段。本库最终结论以下表为准。

```sh
conan graph info --requires=<ref> \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<build-profile> -f=json
# 看 nodes[*].binary: Cache/Download = 有制品; Missing = 没有
```

> 附带发现：仓库里的 `ci/scripts/preflight_check.sh` 和 `scripts/ohc/preflight.py`
> 走的是制品仓 search API，而 R35 明确指出该 API 对 binary 返回不完整。
> 两者都不能替代 `conan graph info`。

### 依赖清单（`binary` 字段实测）

| 依赖 | 版本 | 制品 | 备注 |
|------|------|------|------|
| openssl | 3.5.6.1 | ✅ Cache | 配方含 cmake_file_name=OpenSSL、OpenSSL::Crypto/SSL |
| olm | 3.2.16 | ✅ Cache | 仅 cpp_info.libs=["olm"]，无 cmake_target_name → olm::olm |
| nlohmann_json | 3.12.0 | ✅ Cache | 上游要求 ≥3.11.0 |
| coeurl | 0.3.2 | ✅ Cache | **制品已在 ohpcd**；配方目录尚未合入 main，但不影响本库构建 |
| re2 | 2024-04-01 | ✅ Cache | 真依赖（见 §三.2）；带出 abseil-cpp（Cache） |
| libcurl | 8.5.0 | ✅ Cache | ⚠️ 无 TLS 后端，见 §三.4 |
| libevent | 2.1.13 | ✅ Cache | 提供 libevent_core.pc / libevent_pthreads.pc |
| spdlog | 1.17.0 | ✅ Cache | 上游 `find_package(spdlog 1.0.0 CONFIG)`；带出 fmt |
| fmt | 12.2.0 | ✅ Cache | spdlog 1.17.0 的解析版本，需显式 require（E216 同族） |
| gtest | 1.17.0 | ✅ Cache | test_requires；包内只有 `gtest.pc`（配方仅声明 `libs=["gtest"]`），测试目标改用 CMake 目标 |
| pkgconf | 3.0.6 | ✅ Cache（host） | tool_requires，见 §三.6 |

`conan graph info archives/m/mtxclient/0.10.1 -pr:h=ci/conan/profiles/ohos-aarch64`：
15 个节点、`graph.error=None`、无节点级 error；唯一非 Cache 的是 `mtxclient/0.10.1` 自身（待构建）
与 build 上下文的 `pkgconf`（host 制品为 OHOS，需在设备上解析）。

## 三、关键分析结论

### 1. 必须 C++20，不能跟随 profile 的 cppstd=17

`include/mtx/identifiers.hpp` 用三路比较并依赖 `std::strong_ordering`：

```cpp
auto operator<=>(User const &other) const noexcept { return id_.compare(other.id_) <=> 0; };
```

`ci/conan/profiles/ohos-aarch64` 里是 `compiler.cppstd=17`。库目标虽然自己 `set_property(CXX_STANDARD 20)`，
但 15 个 gtest 可执行文件不设，会落到 17 而编译失败。配方在 `CMakeToolchain` 中显式固定
`CMAKE_CXX_STANDARD=20` / `CMAKE_CXX_STANDARD_REQUIRED=ON`，与上游 toolchain.cmake 的意图一致。

### 2. re2 是真依赖，不能裁剪

上游 CMakeLists 的 `pkg_check_modules(re2 REQUIRED ...)` 不是冗余：
`lib/structs/pushrules.cpp` 里 `#include <re2/re2.h>`，并用 `re2::RE2::GlobalReplace`、
`re2::RE2::Options` 实现 Matrix 推送规则的通配符匹配（`pushrules.cpp:230,239,243,423-466`）。
因此 re2 保留为直接依赖，通过 PkgConfigDeps 生成的 re2.pc 满足 `pkg_check_modules`。

### 3. 上游 toolchain.cmake 与 Conan 工具链不冲突（无需补丁）

`CMakeLists.txt` 第 4-10 行做了：

```cmake
set(CMAKE_TOOLCHAIN_FILE "${CMAKE_CURRENT_LIST_DIR}/toolchain.cmake" CACHE FILEPATH "Default toolchain")
```

而 `toolchain.cmake` 全文只有 3 行（`CMAKE_CXX_STANDARD` / `CMAKE_CXX_STANDARD_REQUIRED` / PIC），
不设编译器、不设 `CMAKE_SYSTEM_NAME`。Conan 通过命令行 `-DCMAKE_TOOLCHAIN_FILE=<conan_toolchain.cmake>`
注入（见 `conan/tools/cmake/cmake.py`），命令行 `-D` 先于 `CMakeLists.txt` 生效写进 cache，
`set(... CACHE ...)` 对已存在的 cache 项不覆盖，因此 Conan 工具链生效、上游文件被忽略，二者不冲突。

### 4. ⚠️ ohpcd libcurl/8.5.0 无 TLS 后端（继承自 coeurl 的分析）

`libcurl/8.5.0` 的 conaninfo 只有 `[requires] zlib/1.3.1.1`（无 openssl），
DT_NEEDED 仅 `libc.so`。结论：该 curl 变体没有 TLS 后端。

影响：mtxclient 本身可正常构建与链接，`check`/离线 API 全部可用；
但真实 Matrix homeserver 一律 HTTPS，运行期会得到 `CURLE_UNSUPPORTED_PROTOCOL`。
本 PR 不尝试修依赖（R36：依赖问题拆到依赖库单独适配），仅在 manifest/PR 中如实记录为已知限制。

### 5. 上游测试分组：6/15 需要真实 Synapse

`tests/meson.build` 明确标注：

- `suite: network`（6 个）：connection / client_api / media_api / e2ee / device / pushrules
- `suite: nonetwork`（9 个）：crypto / errors / requests / responses / messages / voip / events / identifiers / utils

CMake 侧没有等价 label，只在末尾注册 15 个 `add_test()`。配方在 `cmake.test()` 中用
`-E '^(BasicConnectivity|ClientAPI|MediaAPI|Encryption|Devices|Pushrules)$'` 排除网络组，
其余 9 个照常执行。6 个网络二进制仍然编译（保证代码路径可编译），只是不执行。

`Responses` 用例依赖 `tests/fixtures/responses/sync.json`（2.5MB）与 `sync_with_crypto.json`：
上游在 configure 阶段 `file(COPY tests/fixtures DESTINATION ${CMAKE_CURRENT_BINARY_DIR})`，
`fixture_prefix()` 未设 `FIXTURE_PREFIX` 时回退 `"."`，ctest 默认工作目录为 build 目录，可命中。

### 6. ⚠️ OHOS 镜像没有 pkg-config，必须自带 pkgconf

设备实测（裸 SSH 与设置 PATH 后都确认）：

```sh
command -v pkg-config   # → 未找到
command -v pkgconf      # → 未找到
ls /data/service/hnp/bin | grep -i pkg   # → 空
```

而 mtxclient 的 `CMakeLists.txt` 有 5 处 `pkg_check_modules(... REQUIRED ...)`
（re2 / libevent_core / libevent_pthreads / libcurl / coeurl）。
CMake 的 `FindPkgConfig` 模块第一步就是找可执行文件，
找不到就 `Could not find PkgConfig` FATAL —— 这是本库在设备上**真正会挡住构建的点**。

处置：配方把 `pkgconf/3.0.6`（ohpcd 已发布，含 OHOS aarch64 制品 `bin/pkgconf`）作为
`tool_requires` 引入，并在 `generate()` 中把它的绝对路径写进 `PKG_CONFIG_EXECUTABLE`：

```python
def build_requirements(self):
    self.tool_requires("pkgconf/3.0.6")

def _pkg_config_executable(self):
    tool = self.dependencies.build.get("pkgconf")
    if tool and tool.package_folder:
        for name in ("pkgconf", "pkg-config"):
            candidate = os.path.join(tool.package_folder, "bin", name)
            if os.path.exists(candidate):
                return candidate
    return shutil.which("pkg-config") or shutil.which("pkgconf") or ""
```

注意该包只装了 `bin/pkgconf`，**没有 `pkg-config` 这个名字**，所以显式固定路径比依赖
PATH 更稳（CMake 的 `FindPkgConfig` 会优先用 `PKG_CONFIG_EXECUTABLE`）。

## 四、设备可用性与本轮未跑设备构建的原因

W0 通过后本应直接做设备单包验证，但设备在本次会话期间**不空闲**：

| 观测 | 值 |
|------|-----|
| `cat /proc/loadavg` | `21.77 23.92 24.02` |
| 并发运行目录 | `ohos-test-runs/` 下有 `tiger-3.2.4-*`、`medusa-2.3-*` 等他人任务 |
| fork 能力 | 多次出现 `sh: can't fork - try again`、`/bin/grep: Out of memory` |
| runner 锁 | 最近的 `tiger-...-build-direct-...` 是 `echo hi` 探针（rc=0），锁已释放 |

设备侧工具链另有两处与文档不同的现状，需要在跑设备包前纳入考虑：

- `conan` **不在 PATH 上**且没有 console script（`python3 -m conan` 报
  `No module named conan.__main__`）；`python3 -c "import conan"` 可导入，版本 **2.31.1**
  （文档基线是 2.29.1）。需要用 console script 路径或 `python -c` 入口调用。
- `git` 在 `/data/service/hnp/bin/git`，`cmake`/`ninja`/`python3`/`zsh` 在
  `$HOME/usr/local/bin`，都需要显式设 PATH。

按工作流 §5「重任务错峰运行 / 失败后先回本机分析，不连续霸占真机」以及本轮约束
「除非明确拿到真机空闲窗口，先做本机前置工作」，本轮**未抢占设备**，改以
§六 的命令形式交付下一步。

## 五、补丁说明

### patches/0001-cmakelists-lowercase-olm-package.patch

`CMakeLists.txt` 中 3 处 `Olm` → `olm`：

- `find_package(Olm 3.2.7 REQUIRED)` → `find_package(olm 3.2.7 REQUIRED)`
- `set_package_properties(Olm PROPERTIES ...)` → `set_package_properties(olm PROPERTIES ...)`
- `Olm::Olm` → `olm::olm`

根因：libolm 3.2.x 自身安装的是 `olm-config.cmake`；Conan 侧 `olm/3.2.16` 配方未声明
`cmake_target_name`，CMakeDeps 按包名生成 `olm-config.cmake` + `olm::olm`。
大小写不匹配 → `Could not find a package configuration file provided by "Olm"`。
实测证据：`conan install` 生成的 CMakeDeps 目录中为 `olm-config.cmake`，目标为 `olm::olm`。

### patches/0002-cmakelists-gtest-targets.patch

`if(BUILD_LIB_TESTS)` 内 15 个测试目标的
`GTest::GTest` + `GTest::Main` 换成 `GTest::gtest` + `GTest::gtest_main`。

根因：googleTest 1.13 起导出目标改名为 `GTest::gtest` / `GTest::gtest_main`，1.14 删除旧名；
mtxclient 0.10.1（2025-08）仍链接旧名 → `links to target "GTest::GTest" but the target was not found`。
CMakeDeps 为 gtest 包生成的 `gtest-config.cmake` 与 gtest 包自带的 `GTestConfig.cmake`
都导出 `GTest::gtest` / `GTest::gtest_main` 两个当前名，因此改目标名即可。

> 注意：`find_package(GTest)` 的**包名大小写本身不是问题** —— CMake 会同时搜索
> `<Name>Config.cmake` 与 `<name>-config.cmake`，CMakeDeps 生成的 `gtest-config.cmake` 能被命中。
> 真正的问题是目标名。

> 走过的弯路（记录以免重犯）：初版补丁改成 `pkg_check_modules(gtest_main ...)` +
> `PkgConfig::gtest_main`，真机上失败 —— 因为 gtest 包内虽有 `gtest_main.pc`，
> 但配方只声明 `cpp_info.libs = ["gtest"]`，**PkgConfigDeps 只会生成 `gtest.pc`，
> 不生成 `gtest_main.pc`**，`pkg_check_modules(gtest_main ...)` 目标不存在。
> 结论：判断某个 pkg-config 模块能否用，必须以 PkgConfigDeps（或包内 `lib/pkgconfig`）
> 实际产出的 `.pc` 文件名为准，不能以"包里有这个 .pc 文件"为准。

## 六、下一步命令（真机 / shadow CI）

前置条件已满足（W0 全部依赖在 ohpcd 有 OHOS 制品），只差设备空闲窗口。

```sh
# 0) 设备侧准备：把本分支同步到隔离 job
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user "$USER" --job mtxclient-010 \
  --package archives/m/mtxclient/0.10.1 \
  --repo-source "$HOME/validation/build_in_harmonyos"
. "$HOME/ohos-users/$USER/mtxclient-010/env.sh"
export PATH="$HOME/usr/local/bin:/data/service/hnp/bin:$PATH"

# 1) 单包 shadow CI（推荐入口，单包排队）
sh "$HOME/bin/run-ohos-shadow-ci.sh" "$CI_PACKAGES"

# 2) 等价的定向 CI
CI_PACKAGES="archives/m/mtxclient/0.10.1" zsh ci/conan/build_and_test.sh

# 3) 只看 conan create（隔离 CONAN_HOME 内）
conan create archives/m/mtxclient/0.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

设备侧执行前必须确认（首次启动对照避坑指南 + 本会话实测）：

| 检查 | 命令 | 本会话实测结果 |
|------|------|----------------|
| `settings.yml` 认识 OHOS | `conan profile show -pr:h ci/conan/profiles/ohos-aarch64` | 待确认（隔离 job 会复制既有配置） |
| 编译器路径存在 | `ls /data/service/hnp/bin/clang++` | 存在 |
| conan 入口 | 无 console script；`import conan` = 2.31.1 | ⚠️ 见 §四 |
| git / cmake / ninja | `command -v git cmake ninja` | 需显式设 PATH（见上） |
| pkg-config | — | ⚠️ 系统没有；已由 `tool_requires("pkgconf/3.0.6")` 提供 |
| `TMPDIR`/`TMPPREFIX` | 指向 `$RUN_DIR/tmp` | 隔离 runner 会设置 |

预期结果：`Build Summary` `Total: 1`，L0/L1 pass；ctest 执行 9 个 nonetwork 用例全通过，
6 个 network 用例不执行；`bin/` 无产物（纯库，R38 不需要 commands.json）。

## 七、对话记录

### 会话 #1 — 2026-09-29

**目标**：A 类前置适配（W0 依赖检查 + 源码/构建系统分析 + 配方与 test_package + 可行本机验证）。

**已完成**：
- 源码分析：识别 CMake+C++20、5 处 pkg-config 依赖、上游 toolchain.cmake 优先级、
  re2 真依赖、olm/gtest 两处命名不兼容、上游测试 15 个分成 6/9 两组。
- 配方与 test_package 编写完成，产出 2 个补丁。
- 本机静态验证：sha256 校验、配方语法、YAML 解析、2 个补丁对**全新下载源码**顺序 apply 干净、
  依赖图 15 节点无冲突、CMakeDeps/PkgConfigDeps 产物名与 mtxclient 的探测方式逐项对齐、
  test_package 36 项断言所用 API 全部核对过签名与命名空间、本机 CI 门禁复刻 48 项 0 失败。
- 设备连通性与工具链实测：SSH 可达；发现**系统无 pkg-config**（已用 pkgconf tool_requires 解决）。

**纠正记录（重要）**：
- 初次 W0 用 `conan download` 退出码判断，错误地得出「coeurl 未发布 → 本库 blocked」。
  改用 `conan graph info` 读 `binary` 字段后确认 **coeurl/0.3.2 制品已在 ohpcd**，W0 实际通过。
  已在 §一/§二 更正状态与结论，并把方法学教训写进 manifest 的 knowledge_gained。
  教训：**退出码与输出文本都不足以判断依赖可用性**。

**未完成**：
- 设备 `conan create` 与上游 9 个 nonetwork 用例的实际通过率：设备在会话期间处于他人构建
  负载（load ~22、fork 失败）下，按错峰规则未抢占，待空闲窗口执行（命令见 §六）。

**遗留风险**：
- 依赖链上 CMakeDeps 对传递依赖不生成数据（E216 同族），配方已按 coeurl 的做法把各依赖的
  include/lib 目录补到 `cpp_info.includedirs`/`libdirs` 并补 `LD_LIBRARY_PATH`；
  设备首次构建时若仍出现头文件或 .so 找不到，优先查这里。
- `pkgconf` 作为 build 上下文依赖在 Windows 上显示 `Missing` 属正常（host 是 OHOS），
  设备上 build=host=OHOS 时解析为已发布制品；若设备构建报 `pkgconf` 缺失，先确认
  `-pr:b` 也用了 `ci/conan/profiles/ohos-aarch64`。
- 每个补丁只改 CMake 构建系统，未触碰任何源文件；已用 `git apply --check` 对全新下载源码验证。

## 八、知识草稿：查重与新颖性判定（路径 B 交付）

本 PR 按【知识库扩展】口径交付 **4 对**草稿（`knowledge/drafts/E999-draft-MTX{1..4}.kv` + `.md`），
并把 `manifest.yaml` 的 4 条对应 `knowledge_gained` 逐条回填 `# knowledge_ref: <草稿 id>`。
草稿经四范围查重（正式库 `knowledge/graph/E*.kv`、索引 `index.tsv`、`knowledge/drafts/*`、本条候选），
扫描口径：745 个文件（graph 321 + drafts 424）。

### 8.1 查重结果

| # | 候选机制 | 命中 | 判定 |
|---|----------|------|------|
| 1 | OHOS 上 CMake 不实现 `VERSION`/`SOVERSION`（无 `-soname`、无版本化文件名、导出 `IMPORTED_NO_SONAME`） | 2（`DRAFT-openjpeg2-hmdfs-versioned-soname.kv`、`E326-draft-4801.md`） | **新颖**：openjpeg2 讲的是「设了属性后 HMDFS 拒绝建符号链接」，本条讲「平台根本不落实属性」；E326 经人工复核为**正则假阳**（该条目讲 `make` 默认 `SHELL=/bin/sh` 被拒，与 SONAME 无关） |
| 2 | Conan `CppStdBlock` 用**普通** CMake 变量注入标准，遮蔽项目 `cache_variables` | 0 | **新颖**（四范围零命中） |
| 3 | `generators` 必须作为类属性声明，否则静默不生成任何 `*-config.cmake`/`.pc` | 0 | **新颖**（四范围零命中） |
| 4 | 判断依赖是否已发布必须读 `conan graph info` 的 `binary`，`conan download` 退出码会反向 | 1（本 PR 自己的草稿文本） | **新颖**（四范围零命中） |

另有一条**部分重叠、不单独成稿**的机制：

| 候选机制 | 命中 | 判定 |
|----------|------|------|
| `cmake.test()` 走 `cmake --build --target test`，不套 run 环境 | 3（`E298.kv`、`E301.kv`、`E321-draft-78CB.md`） | **因果重叠**：E298 已写「`cmake.test()` 把执行委托给 CTest，配方无法显式控制 conanrun 环境」，E301 已写「`cli_args` 被路由到 `cmake --build`」。本库的增量只是「共享库被测时需要 `env="conanrun"` + 构建目录入 `LD_LIBRARY_PATH`」这一后果，故不单独出稿，仅保留在 `knowledge_gained` |

### 8.2 与最接近既有条目的边界

| 条目 | 讲的是什么 | 与 MTX1 的关系 |
|------|-----------|---------------|
| `DRAFT-openjpeg2-hmdfs-versioned-soname.kv` | 设了 VERSION/SOVERSION 后，HMDFS 工作目录拒绝创建符号链接 → `cmake_symlink_library` 失败；修法是关闭版本化 | 互补：该条的失败点在「建链接」，MTX1 的失败点在「CMake 不生成 soname 与版本化文件名」。**openjpeg2 的修法（跳过 VERSION/SOVERSION）不能修好「库缺 DT_SONAME」**，两套观测同时成立才完整 |
| E207 | HarmonyOS CMake 链接同项目内库时用相对路径而非 SONAME | MTX1 给出该现象的底层原因与可复现判据（最小工程 + `llvm-readobj`） |
| E274 | 打包时漏 SONAME 符号链接，运行期解析 NEEDED 失败 | MTX1 的第 3 步正是该失效模式在 OHOS 上的成因 |
| E050 | HMDFS 符号链接不可靠 | MTX1 据此要求用真实文件而非符号链接 |
| E216 | Conan/CMakeDeps 对传递依赖不生成数据 | MTX2/MTX3 与之同族但机制不同（标准注入 / 生成器未声明） |

### 8.3 七轴新颖性（MTX1..MTX4）

| 轴 | MTX1 SONAME | MTX2 C++ 标准 | MTX3 generators | MTX4 W0 判据 |
|----|-------------|---------------|-----------------|--------------|
| exact_duplicate | false | false | false | false |
| causal_duplicate | false | false | false | false |
| trigger_overlap | partial（openjpeg2：同涉 VERSION/SOVERSION） | none | none | none |
| solution_overlap | partial（openjpeg2 关版本化 vs 本条显式补 soname） | none | none | none |
| combination_novelty | true | true | true | true |
| boundary_novelty | true | true | true | true |
| test_migration_novelty | true | true | true | true |

### 8.4 为何具备路径 B（贡献创新）价值

4 条全部是**平台/工具链层可复用判据**，不是单库的编译参数修补：

1. MTX1 是 OHOS 平台行为（CMake 不实现 VERSION/SOVERSION），对任何在 OHOS 上用 CMake 构建共享库的库成立；
2. MTX2 是「recipe 设置被工具链覆盖」这一**类**问题，可迁移到其他由 `self.settings` 派生的项；
3. MTX3 揭示「**静默不执行**比报错更贵」的诊断顺序（先看生成器产出，再查依赖发布状态）；
4. MTX4 纠正了一条被仓库脚本沿用的 W0 判据（`ci/scripts/preflight_check.sh` 与
   `scripts/ohc/preflight.py` 走的 search API 同样不完整），直接影响所有适配任务的依赖检查结论。

四条都有本任务的一手证据（最小复现工程、真机日志、RUN_DIR），非推测。
