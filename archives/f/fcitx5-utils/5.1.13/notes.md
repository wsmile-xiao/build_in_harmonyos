# fcitx5-utils 5.1.13 适配笔记

## 背景

- `fcitx5-utils` 是 **fcitx5 源码树内的 `Fcitx5Utils` 组件**（`src/lib/fcitx-utils/`），没有独立的上游发布仓库（分析端核验 `GET https://api.github.com/repos/fcitx/fcitx5-utils` → 404）。
- 本依赖包为 `libime-jyutping 1.0.18`（父库，W0 门禁实测 `dependency_missing`）与 `libime 1.1.12` 解除阻塞的最底层依赖。
- 依赖链：`fcitx5-utils 5.1.13`（本任务，最底层）→ `libime 1.1.12` → `fcitx5 5.1.13` → `libime-jyutping 1.0.18`。
- 官方上游与 tag：`https://github.com/fcitx/fcitx5`，tag `5.1.13`（annotated tag object `591212e3…`，commit `0f26cf32…`）。执行端实际下载 `fcitx5-5.1.13.tar.gz` 并核验 SHA-256 = `7621a7e4ea5545591fa8a5b1913ce1f7aec51158104a4fb1a28a7fe5b61c2fb6`。

## 组件边界（用户已确认，2026-09-22）

- 独立成包：`archives/f/fcitx5-utils/5.1.13/**`，交付分类 `【依赖项】`、PR-only、`issue_action: none`。
- 同源 `fcitx5/5.1.13`（Fcitx5Core/Fcitx5Module）另行独立任务，不在本包范围；本包只含 Fcitx5Utils 库 + 头文件 + CMake 包配置 + pkg-config。
- 版本陷阱：必须精确 `5.1.13`，不得写成 5.1.10/5.1.12/5.1.14/5.1.15 或其他 tag。

## 导出契约

- `src/lib/fcitx-utils/CMakeLists.txt` L143 `add_library(Fcitx5Utils …)`，别名 `Fcitx5::Utils`，`install(TARGETS Fcitx5Utils …)` + CMake 包配置 `Fcitx5UtilsConfig.cmake` / `Fcitx5UtilsConfigVersion.cmake`（ecm_setup_version 生成）+ `Fcitx5Utils.pc` + 头文件到 `include/Fcitx5/Utils/fcitx-utils`。
- 纯库组件（无 `add_executable`），导出 `Fcitx5Utils` / `Fcitx5::Utils`，父库 `find_package(Fcitx5Utils 5.1.13 REQUIRED)` 可命中。
- 组件私有链接：`DL::DL LibIntl::LibIntl Pthread::Pthread`（+ 可选 LibKVM / dbus / libuv 事件循环后端，本配置全部关闭）。

## 构建方案

上游组件 CMakeLists 设计为从 fcitx5 顶层并入；顶层需 ECM/pkg-config/XKB 等大量依赖，无法整体构建。本配方在 `source()` 中整理 **staging 独立构建根**，零改动上游源码：

```
staging/
├── CMakeLists.txt      # 配方生成的 wrapper（等价复刻顶层上下文）
├── config.h.in         # 顶层 config.h.in，configure_file → config.h
├── cmake/              # 顶层 cmake/ find 模块 + Fcitx5CompilerSettings.cmake
└── fcitx-utils/        # 组件本体（原样复制）
```

wrapper 关键点：
- `find_package(ECM REQUIRED 1.0.0)` + `include(ECMSetupVersion)`：ecm_setup_version 生成 Fcitx5UtilsConfigVersion.cmake（SOVERSION 2）；ECM 通过 `tool_requires extra-cmake-modules/6.19.0`（ohpcd 已发布）。
- `CMAKE_MODULE_PATH` 指向上游 `cmake/`（FindDL/FindLibIntl/FindPthread/Fcitx5CompilerSettings）。
- `FCITX_INSTALL_*` 系列变量沿用顶层定义（Fcitx5UtilsConfig.cmake.in 引用）。
- `config.h.in` 生成（组件多个源文件 `#include "config.h"`；HAVE_PIPE2/HAVE_SYS_* 用 check_* 探测）。
- `ENABLE_DBUS=Off`、`EVENT_LOOP_BACKEND=none`（OHOS 无 dbus/libuv/systemd 需求，event_none.cpp 内置零外部事件循环依赖）。

## 依赖（W0 门禁实测）

| 依赖 | 版本 | ohpcd 状态 | 用途 |
|---|---|---|---|
| gettext | 0.22.5.1 | ✅ 已发布（含 binary） | libintl（i18n.cpp 的 gettext/dgettext；OHOS libc 无 dgettext、sysroot libintl.h 空壳无声明） |
| extra-cmake-modules | 6.19.0 | ✅ 已发布 | ECM / ecm_setup_version（tool_requires，构建期） |
| DL/Pthread | — | OHOS sysroot 自带 | dlfcn.h / pthread.h 头与 libc 内符号 |

## 鸿蒙特有测试

`test_package/test_fcitx5_utils.cpp`：find_package + 链接 Fcitx5::Utils + 真机运行，调用
stringutils::trim / Key::fromString / Semver::parse / StandardPaths（standardpaths_p_unix.cpp
平台路径路径）真实 API 并断言。本机为 aarch64 HarmonyOS，可执行文件原生运行（非 cross-building）。

## 上游测试说明

Fcitx5Utils 组件内无 `add_executable`、无测试目录（`testing.h/cpp` 是给 fcitx5 core 用的测试框架工具，非本组件测试）。
fcitx5 顶层 `test/` 属 fcitx5 core 范畴（另立任务）。故上游测试台账：组件无对应可运行测试入口，如实单列，不虚报通过。

## 未完成项

- 无。等待 Conan 流水线（conan create / conan-verify / finish / W2/W3）实际执行结果回填。

## 知识路径判定（executor_local_required，2026-09-22）

快照：外置只读稀疏（repository=build_in_harmonyos main @ 48d9cee6，sparse=knowledge），
正式 graph 540 条 + 草稿 1940 文件全部扫描。

候选（本任务真实错误→根因→修复→触发→验证→边界）全部等价命中既有成对草稿：

| 候选 | 等价草稿 | 判定 |
|---|---|---|
| OHOS libc++15 缺 std::ranges 算法 | DRAFT-E5xx-ohos-libcpp-missing-ranges-algorithms | 等价命中 |
| OHOS libc++15 `<format>` stub | DRAFT-ohos-libcxx15-format-ranges-capability-gap | 等价命中 |
| std::views 缺失 | DRAFT-ohos-libcxx-missing-std-views | 等价命中 |
| hash&lt;filesystem::path&gt; 缺失 | DRAFT-dawn-…-libcxx15-cpp20-compat-ensemble | 等价命中 |
| sysroot libintl.h 空壳 / libc 无 gettext | DRAFT-13410-trueprint-libintl-stub-header | 等价命中 |

结论：`knowledge_decision: reuse_existing`（路径 A 语义），不创建草稿。
本任务是【依赖项】分类：保持 PR-only、标题【依赖项】、`issue_action: none`，
不叠加路径 A/B/C 前缀。审计全文：`/storage/Users/currentUser/tmp/fcitx5-utils-r01/logs/knowledge-decision.json`。
---

**编译结束**: 2026-09-22 22:13
**最终状态**: built
