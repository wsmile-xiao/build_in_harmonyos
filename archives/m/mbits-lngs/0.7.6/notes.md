# mbits-lngs 0.7.6 适配笔记

## 编译环境
- 构建系统: cmake (C++17)
- manifest 原始归档构建日期: 2026-09-23；首次手工编译完成: 2026-09-28；首次独立 Conan create 完成: 2026-09-30
- 最近测试复核: 2026-10-04（上游全量测试 2026-10-03；Conan 选项兼容性复核 2026-10-04）
- 编译器: clang 15.0.4 (aarch64-linux-ohos 交叉工具链)
- 状态: published
- Conan: 2.29.1 (OHOS 适配版, os=OHOS 枚举)
- CMake/CTest: 4.4.3（test_package 保守最低要求 3.20；生成表达式支持依据与链接统一见 reports/test-report.md）；pkg-config: 3.0.7（HarmonyOS PC 真机）
- test_package 的 `PkgConfigDeps` 消费者构建为可选覆盖：检测到 `pkg-config` 与生成的 `lngs.pc` 时编译链接；缺少任一项时不阻断 CMake 配置。HarmonyOS PC 已实测通过。

## 编译步骤

以下是上游 tag 日期为 2026-09-23、实际于 2026-09-28 完成的历史手工构建命令，不是 Conan 最终包配置；Conan 最终配置仅构建静态核心库（`LNGS_LITE=OFF`），以本目录 `conanfile.py` 和版本 manifest 为准。**下列命令仅供复核历史记录；复制做当前构建时应使用最终 Conan 配方，不能沿用历史 `LNGS_LITE=ON`。**

```bash
# 历史配置：LNGS_LITE=ON；不代表最终交付包配置。
# 1. 官方源码获取（github.com 直连超时 → 官方 codeload 通道 + SHA-256 核验）
curl -fsSL "https://codeload.github.com/mbits-os/lngs/tar.gz/refs/tags/v0.7.6" \
  -o ~/tmp/builds/mbits-lngs-0.7.6.tar.gz
# SHA-256: 85c9fd3afd5b6d5446a294f4de11221ae7fa160a62d1115a7ea0c1af17633a0b

# 2. 核心库编译（零外部依赖）
DEFAULT_PREFIX="${DEFAULT_PREFIX:-$HOME/.local}"  # 历史手工安装前缀，可用环境变量覆盖
cmake -S . -B build-lib -DLNGS_TESTING=OFF -DLNGS_APP=OFF -DLNGS_LITE=ON \
      -DLNGS_INSTALL=ON -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
cmake --build build-lib -j2    # 历史手工构建（LNGS_LITE=ON），与最终 Conan 包配置不同

# 3. 配方验证 + W3 本地 CI
python3 scripts/ohc-run.py conan-verify mbits-lngs 0.7.6    # G1-G4 PASS
python3 scripts/ohc-run.py finish mbits-lngs 0.7.6 published # W3 隔离复验后通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务头上游 URL https://github.com/mbits-libs/lngs 返回 404 | 上游 org 实际为 mbits-os（mbits-libs org 无 lngs 仓库） | GitHub API 搜索确认 mbits-os/lngs（Language strings support），tag v0.7.6 与任务版本精确匹配，codeload 实测可下载且 SHA-256 一致 |
| 2 | github.com 直连下载超时 | HarmonyOS 真机网络无法稳定访问 github.com | 配方改用官方 `codeload.github.com` 归档 URL，并在 Conan `get()` 显式声明 `.tar.gz` 文件名；与 v0.7.6 官方归档 SHA-256 一致 |
| 3 | app 与上游测试的部分精确依赖版本未发布 | mbits-args/utfconv/diags/mstch 的需求版本未在 2026-09-30 registry 查询到；fmt 与 mbits-semver 可用 | 核心库零外部依赖，独立交付；未运行的上游入口如实登记，不声明全量通过 |
| 4 | LNGS_TESTING=ON 无法 include tools/testing/googletest.cmake | tools/testing 与 tools/coveralls 为 git 子模块，官方 tag 归档为空占位目录 | 打包构建 LNGS_TESTING=OFF；test_package 用公开头 <lngs/plurals.hpp> API 做 6 项检查，并运行共享消费者检查；static-library 配置真机 CTest 2/2 通过，另有 pkg-config 消费者编译链接检查 |
| 5 | W3 JC 门禁 full 模式命中其他库基线文件（cloog/kics 的 .build-closed/.staging-verified） | 分支无 commit 时 junk_check 回退 git ls-files 全仓扫描，main 已提交的其他库基线文件被误报 | 基线隔离复验：记录 pre-SHA-256 → 临时隔离 → 复跑 W3 通过 → 原样恢复；post-SHA-256 与 pre 一致（空文件 SHA-256 `e3b0c442…`），未提交/未修改基线文件 |

## 源码修改

无（纯库交付，无需补丁；构建选项经配方 generate() 控制）

## 依赖版本

- 核心库零外部依赖；HarmonyOS PC Clang `-stdlib=libc++` 工具链选择所需 C++ ABI runtime
- 2026-09-30 registry 查询：mbits-semver/0.1.1、fmt/9.1.0 与兼容测试包 gtest/1.17.0.2 可用；mbits-args/0.12.3、mbits-utfconv/1.0.3、mbits-diags/0.9.6、mbits-mstch/1.0.4、gtest/cci.20210126 未找到精确版本。上游 `conanfile.txt` 请求的 `gtest/cci.20210126` 未找到；2026-10-03 全量 CMake 测试使用源码构建的 GoogleTest 1.17.0，二者不是同一依赖版本，详见 `reports/test-report.md`。

## 验证结果

### 历史手工构建（非最终 Conan 配方配置）

```bash
# 警告：此历史手工构建使用 LNGS_LITE=ON；最终 Conan 交付配置为 LNGS_LITE=OFF.
$ cmake --build build-lib -j2  # LNGS_LITE=ON，exit 0
# 2026-09-30 独立 CONAN_HOME 下 conan create 成功；当日旧版消费者测试为 1/1。
# 上游子集测试旧结果为覆盖 7/49（所选子集内 7/7 声明通过）；已被后续全量结果取代。
```

### 仓库门禁与最终包验证

```bash
$ python3 scripts/ohc-run.py lang-preflight mbits-lngs 0.7.6 --src $BUILD_SRC_DIR  # exit 0 (cpp)
$ python3 scripts/ohc-run.py conan-verify mbits-lngs 0.7.6                           # exit 0 (G1-G4)
$ python3 scripts/ohc-run.py finish mbits-lngs 0.7.6 published                       # exit 0
# 最终包：LNGS_LITE=OFF；HarmonyOS 真机 conan create 退出码 0，test_package CTest 2/2。
# 上游全量：GoogleTest 49/49 声明、402/402 实例；命令行 CTest 18/20，1 跳过、1 失败。
# 历史探测：OHOS Conan 2.29.1 曾接受旧修订中未声明的 shared=True。实际探测中 Conan static-library 包类型约束先返回配置错误；recipe validate() 也显式拒绝 shared=True；CI 不注入该选项。
```

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/m/mbits-lngs/0.7.6/conanfile.py` 与 `conandata.yml` | 仓库根相对路径；CMake 配方（官方 archive URL + SHA-256） |
| `archives/m/mbits-lngs/0.7.6/manifest.yaml` 与 `test_package/MANIFEST.yml` | 仓库根相对路径；版本构建与测试口径、test_package CI 门禁说明 |
| `archives/m/mbits-lngs/commands.json` | 仓库根相对路径；声明该交付为 library 且无 CLI 二进制 |
| `archives/m/mbits-lngs/0.7.6/test_package/` | 仓库根相对路径；消费者验证（公开 plurals API 与共享消费者运行） |
| `archives/m/mbits-lngs/0.7.6/reports/test-report.md` | 仓库根相对路径；上游 GoogleTest、CTest 与 Conan 消费者测试台账 |
| `archives/m/mbits-lngs/0.7.6/reports/verify_lite_scope.py` 与 `lite-scope-verification.txt` | 仓库根相对路径；官方归档 SHA 校验及 LNGS_LITE/CMake 结构复核脚本与输出 |
| `knowledge/drafts/DRAFT-mbits-lngs-family-core-first-delivery.{md,kv}` | 仓库根相对路径；路径 B 知识草稿 |

## 编译标准边界

配方固定 `CMAKE_CXX_STANDARD=17`；profile 声明更高 `compiler.cppstd` 只表示编译器具备该能力，配方源码仍以 C++17 编译。

## Conan 版本边界

固定 `package_type="static-library"` 时声明 `shared` 选项及其拒绝行为，已在 OHOS 适配版 Conan 2.29.1 上完成正反向实测；移植到标准发行版或其他 Conan 版本前，应重新验证该组合的选项校验行为。新增支持平台时，应同步调整根配方与 test_package 的 `validate()`，并复跑消费者测试。

## 注意事项

- `mbits-args/0.12.3`、`mbits-utfconv/1.0.3`、`mbits-diags/0.9.6`、`mbits-mstch/1.0.4` 与 GoogleTest 的目标版本可从 registry 获取后，follow-up 可恢复 LNGS_APP/LNGS_TESTING=ON 复跑受影响入口；`fmt/9.1.0` 与 `mbits-semver/0.1.1` 已在 registry 可用。
- 非 CLI 交付：app 因依赖未发布未构建；软件级 commands.json 的 type=library、binary=false，仅满足本任务的 L0 文件存在性自检，不声称存在命令行二进制。

---

**首次编译结束**: 2026-09-28 10:12
**历史状态记录（2026-09-28）**: published

## 2026-10-03 真机补测更新

- 已从官方提交自建 mbits-args/0.12.3、mbits-diags/0.9.6、mbits-utfconv/1.0.3、mbits-mstch/1.0.4，并还原 `tools/testing`、`tools/coveralls` 的精确子模块提交；摘要、提交与完整命令见 `reports/test-report.md`。
- 采用 `LNGS_APP=ON`、`LNGS_TESTING=ON`、`LNGS_LINKED_RESOURCES=ON` 真机全量运行：上游 GoogleTest 声明 49/49 通过（lib 25、app 24），测试实例 402/402 通过（196+206）。Conan 消费者测试另计；更新后在 static-library 配置下 CTest 2/2 通过，含六项主消费者检查及共享消费者运行检查；pkg-config 消费者另行编译链接通过，不计入 CTest。正式 Conan 包配置使用 `LNGS_LITE=OFF`，仅交付静态核心库。此前 shared=True 探测仅产出静态核心归档；最终配方声明 shared=False 以阻止 profile 静默注入，并拒绝 shared=True。
- CTest 命令行 fixture 18/20 通过；`0028-no-shared-data-enum.json` 按上游 `skippable: true` 标记跳过；`0027-no-shared-data.json` 实际输出 `unknown command: --share`，而预期为 `command missing`。此结果独立于 49 个 GoogleTest 声明，PR 正文和 manifest 分开披露；后续启用 CLI 时复核该 fixture 并更新此项记录。
- 初次外置模板构建未安装模板而造成的空输出已由内嵌模板全量重跑纠正，不以初次失败作为最终 GoogleTest 统计。
