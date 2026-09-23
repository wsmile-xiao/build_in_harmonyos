**DRAFT-gtest-1-17-0-1-cmake-components — Conan CMakeDeps 的 GTest 组件导出契约**

当 googletest 被作为 Conan 依赖消费时，旧配方只导出 lowercase `gtest::gtest`，但上游消费者通常请求 `find_package(GTest CONFIG)` 并链接 `GTest::gtest_main`、`GTest::gmock`。仅能生成包或链接单个库不能证明该依赖契约可用；必须同时验证配置文件名、四个组件目标及其依赖关系。

**身份与当前结论**

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-gtest-1-17-0-1-cmake-components` |
| 配套结构化文件 | `knowledge/drafts/DRAFT-gtest-1-17-0-1-cmake-components.kv` |
| 当前状态 | 已有验证证据待审 |
| 建议去向 | 新增模式 |
| 实际贡献者 | `zxyAtom` |
| 来源任务/PR | https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/8612 |
| 提取方式 | 已有普通 PR 升级 |
| 本次交付 PR | 原位升级 #8612 |
| 包及配方版本 | `gtest` / `1.17.0.1` |
| 上游版本与源码 | v1.17.0；https://github.com/google/googletest；SHA256 `65fab701d9829d38cb77c14acdc431d2108bfdbf8979e40eb8ae567edf10b27c` |
| 知识来源提交 | `955c6872def6495ac549a83817613dafe756c90b` |
| 被验证提交 | `955c6872def6495ac549a83817613dafe756c90b` |
| 最后更新 | 2026-09-06 |

本草稿的验证结论是：#8612 的 `test_package` 能通过 `find_package(GTest CONFIG)`、`GTest::gtest_main` 和 `GTest::gmock` 完成配置、链接及运行，CI #41096 的 L0、L1 和 Conan test_package 均通过。仍未证明：#8612 当前 HEAD 重新执行了完整的 65 个上游测试二进制；正文中的 59/65 是既有 gtest/1.17.0 的历史 OHOS 记录。

**从普通 PR 提取的依据**

原 PR 标题、状态与提取基线：`【依赖项】fix(gtest): 1.17.0.1 修复 GTest CMake 导出`，open，HEAD `955c6872def6495ac549a83817613dafe756c90b`。

| 原 PR 事实 | 具体位置与版本 | 提炼出的可复用机制 | 本次补充 |
|---|---|---|---|
| `package_info()` 设置 `cmake_file_name=GTest`，声明四个组件及 `requires` | `archives/g/gtest/1.17.0.1/conanfile.py`，来源提交 `955c6872` | CMakeDeps 的配置文件名、目标名和组件依赖必须与上游 GTest 消费契约一致 | 新增本草稿并与 E292 去重 |
| 消费者使用 `find_package(GTest REQUIRED CONFIG)`，链接 `GTest::gtest_main` 与 `GTest::gmock` | `archives/g/gtest/1.17.0.1/test_package/CMakeLists.txt`，`test.cpp` | 依赖包验证必须覆盖真实下游目标，而不是只检查头文件或单个静态库 | CI #41096 重新验证 1/1 消费者测试 |
| OHOS `/tmp` 只读补丁 | `patches/0001-tmpdir-ohos-sandbox.patch` | 属于已有 GTest/CTest TMPDIR 运行时边界，不是本草稿的新知识 | 与 E292 的 GTest TMPDIR 范围重复，不作为增量 |

原 PR 已有的贡献：新增 `gtest/1.17.0.1` 配方，保持上游 gtest/gmock 测试构建，修复 OHOS 临时目录，并添加 CMake 消费者测试。本次提炼新增的是可迁移的 Conan CMake 导出契约表达和消费者验证边界。

历史记录与本次实验的区分：CI #41096 和提交内容来自原 PR；本次没有重跑 OHOS 构建，仅生成知识材料、执行静态去重和草稿预审。

升级依据：原 PR 的导出改动解决了独立于 TMPDIR 的下游配置契约问题，且 test_package 对四组件中的 `gtest_main` 与 `gmock` 进行了真实消费验证；已有 E292 仅覆盖测试框架运行环境，不覆盖 CMake 导出命名和组件关系。

**1. 触发条件与可辨认现象**

| 条件 | 本次实际值 | 为什么影响结论 |
|---|---|---|
| 目标系统、架构、运行域 | HarmonyOS PC/aarch64，Conan test_package | 需要验证 OHOS Conan 包能被下游 CMake 消费 |
| 编译器及构建工具 | Conan 2、CMake、C++17、CMakeDeps | 导出文件和目标名由 CMakeDeps 生成 |
| 关键依赖及版本 | googletest v1.17.0，包修订 1.17.0.1；无外部 Conan 依赖 | 版本修订改变导出契约而非上游 API |
| 文件系统、路径、权限或硬件 | CI worker 的 OHOS 沙箱；测试临时目录通过 `TMPDIR` 指定 | `/tmp` 边界属于独立运行时补丁 |
| 最小输入与前置步骤 | `find_package(GTest REQUIRED CONFIG)`；链接 `GTest::gtest_main`、`GTest::gmock` | 直接触达下游配置和组件关系 |

首次可定位的失败：原始 lowercase 导出与上游 `GTest` 配置契约不一致；#8612 没有保留旧版本失败日志，因此这里不伪造错误输出，使用导出文件和消费者入口作为静态触发证据。

```text
find_package(GTest REQUIRED CONFIG)
target_link_libraries(test_gtest PRIVATE GTest::gtest_main GTest::gmock)
```

建议错误签名：`GTest::gtest_main|GTest::gmock|cmake_file_name.*GTest`。签名用于识别导出契约，不将普通 `failed` 或包名作为错误匹配。

**2. 根因与排除项**

旧版本 `gtest/1.17.0` 的 `package_info()` 只设置 lowercase `cmake_file_name=gtest` 和 `gtest::gtest` 目标；上游及 zxing-cpp UnitTest 使用标准 `GTest` 配置和 gtest/gmock 组件。Conan 生成的 CMake 文件因此不能提供完整目标契约。#8612 设置 `cmake_file_name=GTest`，为四个实际静态库声明组件，并通过 `requires` 保留 `gtest_main -> gtest`、`gmock -> gtest` 关系；该机制由消费者 CMake 和二进制运行共同验证。

| 可能原因 | 检查方法与证据 | 结论 |
|---|---|---|
| OHOS `/tmp` 不可写 | `0001-tmpdir-ohos-sandbox.patch` 与 E292 对照 | 是独立运行时边界，不是 CMake 导出增量 |
| 库文件缺失或头文件不可见 | #8612 CI #41096 的 L0/L1/test_package | 已排除为本次消费者通过的主要原因 |
| CMake 配置名/目标名不匹配 | 对比旧 `gtest` 导出和新 `GTest` 组件声明；消费者显式请求四组件 | 根因成立 |

**3. 最小修复与选择条件**

1. 在 Conan `package_info()` 设置 `cmake_file_name` 为 `GTest`。
2. 为 `gtest`、`gtest_main`、`gmock`、`gmock_main` 声明实际库、标准 CMake 目标名和组件依赖。
3. 使用真实下游的 `find_package(GTest CONFIG)` 和至少一个 gmock matcher 断言验证配置、链接和运行；不要把只包含 `<gtest/gtest.h>` 的编译当作导出契约验证。

实际修复来源：PR #8612 提交 `955c6872def6495ac549a83817613dafe756c90b` 的 `archives/g/gtest/1.17.0.1/conanfile.py`。

```sh
cmake -S test_package -B build -DCMAKE_PREFIX_PATH=<conan-package>
cmake --build build
./build/test_gtest
```

上面的命令适用于已生成 CMakeDeps 文件且可运行目标 ELF 的 Conan test_package；OHOS 真机执行还需要 CI 提供的运行环境和签名条件。未验证回退方案。

**4. 验证矩阵与证据绑定**

| 证据 ID | 类型 | 提交、环境与输入 | 命令/测试入口 | 实际结果 | 日志/附件、定位与哈希 |
|---|---|---|---|---|---|
| EVID-01 | static | #8612 HEAD `955c6872` | 审查 `conanfile.py` 的 `package_info()` | 四组件和 `GTest` 配置名已声明 | PR 文件 API；提交 SHA 同上 |
| EVID-02 | historical target-executed | #8612 HEAD，OHOS CI worker | Conan `test_package` | 1/1 通过，L0/L1 通过 | CI #41096：https://ohpcd.atomgit.com/ci?id=41096 |
| EVID-03 | historical target-executed | 原 gtest/1.17.0 记录 | 上游 CTest 二进制 | 59/65；6 项因输出、异常配置或共享库场景未通过 | #8612 正文；不是当前 1.17.0.1 HEAD 重跑 |

**被验证文件范围**

| 文件或输入 | 验证时版本/哈希 | 与当前提交的关系 |
|---|---|---|
| `archives/g/gtest/1.17.0.1/conanfile.py` | PR HEAD `955c6872` | 相同 |
| `archives/g/gtest/1.17.0.1/test_package/CMakeLists.txt`、`test.cpp` | PR HEAD `955c6872` | 相同 |
| `archives/g/gtest/1.17.0.1/patches/0001-tmpdir-ohos-sandbox.patch` | PR HEAD `955c6872` | 与导出契约正交；相同 |

被验证提交之后的变化：本次只增加知识草稿和证据报告，未改变上述实现、测试或依赖输入；最终远端 HEAD 会在升级回执中记录。

**测试统计**

| 测试层与明确范围 | 计数单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 库存依据及未执行原因 |
|---|---|---:|---:|---:|---:|---:|---|
| 上游 googletest/googlemock（历史基线） | 测试二进制 | 65 | 59 | 6 | 0 | 0 | #8612 正文继承 gtest/1.17.0 的 OHOS 记录；6 项为输出格式、socket 标志、XML 顺序、异常编译和共享库场景差异 |
| #8612 已安装包消费者 | 测试程序 | 1 | 1 | 0 | 0 | 0 | CI #41096 的 `test_gtest`，覆盖 GTest::gtest_main、GTest::gmock 和 matcher |
| 修复边界与反例 | 导出契约 | 2 | 1 | 0 | 0 | 1 | 新导出路径已验证；旧 lowercase 导出只作静态对照，未在本次 CI 中重新构建失败样本 |

结论的证据等级与限制：导出字段和消费者入口为当前提交静态证据；消费者 1/1 和 L0/L1 为 CI #41096 的历史目标执行证据；完整上游 65 项不是当前 HEAD 重跑。

**5. 适用边界与禁止做法**

| 可复用前提 | 已验证范围 | 未验证或不适用范围 |
|---|---|---|
| 下游使用 CMake CONFIG 模式和标准 GTest 组件 | Conan CMakeDeps、静态 gtest/gmock、C++17 | 非 CMake 消费者、仅 pkg-config、共享库选项组合未在本 PR 重跑 |
| 组件库实际安装且 `requires` 与链接关系一致 | 四组件声明、消费者 1/1 | 其他 googletest 大版本需重新核对上游导出名 |

| 错误做法 | 为什么不成立 | 可观察后果 |
|---|---|---|
| 只导出 `gtest::gtest` 或只复制 lowercase 配置文件 | 配置文件名、gmock 组件和组件依赖仍缺失 | `find_package(GTest CONFIG)` 或 GMock 消费者配置/链接失败 |
| 只运行包内上游测试，不运行消费者 CMake | 上游测试不读取 Conan 生成的下游导出 | 能构建但下游无法发现标准目标 |

**6. 与已有知识的关系及增量**

| 已核验的条目/草稿/前序PR | 已有内容 | 本次新增机制、边界或证据 | 建议处理 |
|---|---|---|---|
| E292，`knowledge/doc/E292.md` | GTest/CTest 测试迁移、TMPDIR、动态库和测试数据边界 | Conan CMake 配置文件名、四组件导出和真实消费者契约 | 新增 |
| gtest/1.17.0 `PR_DESCRIPTION.md` | 静态库打包、历史 59/65 上游记录、TMPDIR 补丁 | 从 lowercase 导出升级为标准 `GTest` CMakeDeps 组件契约 | 新增 |

检索范围与关键词：`knowledge/graph`、`knowledge/doc`、`archives/g/gtest`；关键词 `gtest`、`GTest::`、`CMakeDeps`、`cmake_file_name`、`component`、`SONAME`。命中 E292 和旧 gtest 适配，但未命中同一 CMake 导出组件机制。

这不是同一任务重提或单纯版本修订：1.17.0.1 是对已发布 gtest/1.17.0 导出契约的独立修订。TMPDIR 适配复用 E292，不重复计作增量。

**7. 来源索引与提交自检**

| 材料 | 路径或链接 | 固定版本及角色 |
|---|---|---|
| 上游源码 | https://github.com/google/googletest | v1.17.0；SHA256 如上 |
| 修复实现 | PR #8612 `conanfile.py` | `955c6872` |
| 消费者测试 | PR #8612 `test_package/` | `955c6872`，CI #41096 |
| 汇总证据报告 | `archives/g/gtest/1.17.0.1/reports/knowledge-evidence.md` | 本次升级新增 |
| 原始验证记录 | https://ohpcd.atomgit.com/ci?id=41096 | Conan test_package、L0、L1 通过 |

提交前填写真实检查结果：

- [x] ID、两个文件名和 KV 的 `doc_file` 一致。
- [x] KV 字段均为单行，根因、签名、方案与本文一致。
- [x] 来源 PR、提交、包路径和测试入口可回溯；新增证据报告随升级提交。
- [x] 包版本、验证提交及正文测试统计区分当前消费者验证和历史上游记录。
- [x] 已搜索 E292、旧 gtest 适配及 CMake/SONAME 相关材料，明确新增范围。
- [x] 普通 PR 升级来源提取表已填写。
- [ ] PR 创建后远端文件核对：本地准备阶段尚未完成，待 API 上传后复核。

最终处理建议：作为 `gtest` CMake 导出组件契约的新知识候选提交，TMPDIR 内容保留为原适配贡献并标注与 E292 重复。
原 PR 升级建议：支持原位升级；#8612 仍为 open，源分支不变，CI #41096 已通过但人工审批和 `can_merge_check` 尚未满足。
剩余问题及下一项具体动作：上传本对草稿及证据报告，运行 `draft-review`/格式检查，更新 #8612 标题和正文并回读远端 HEAD、文件和正文。
