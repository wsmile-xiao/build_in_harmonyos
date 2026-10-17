# Knowledge Candidate Ledger — cassiopee-c 1.0.9

**日期**: 2026-09-25
**任务**: cassiopee-c-1.0.9-r01-pc1-43-20260924T215916Z（知识库扩展候选评估）
**执行端**: pc1-43 @ build_in_harmonyos worktree `feat/cassiopee-c-1.0.9`
**任务头**: task_type=知识库扩展 | initial_pr_prefix=【知识库扩展】 | knowledge_candidate_observation=required

## 一、知识候选台账（逐项非噪声候选）

### 候选 1: glog 0.7.x flags.h 的 DECLARE_string 宏在 C++17 下必须前置包含 <string>

- **真实错误**: 编译报 `cannot define or redeclare 'string' here because namespace 'fLS' does not enclose namespace 'std'`、`unknown type name 'GLOG_EXPORT'`（cassiopee.cxx/cassie.cxx 首行即 `<glog/logging.h>`，随后展开 flags.h 的 DECLARE_string 宏）；日志 SHA-256 见 notes.md
- **根因**: glog 0.7.x `glog/flags.h` 的 `DECLARE_string(name)` 宏展开 `extern GLOG_EXPORT std::string& FLAGS_name;`，依赖 `<string>` 已先行包含且 glog 消费宏 `GLOG_USE_GLOG_EXPORT` 已定义；上游 cassie.cxx/cassiopee.cxx 在包含 `<glog/logging.h>` 前未包含 `<string>`（C++17 下 libc++ 不会自动前向提供），且直链未走 CMakeDeps 目标时宏缺失
- **修复**: 补丁 0002/0003 在 `<glog/logging.h>` 前加 `#include <string>`；conanfile generate() 注入 `-DGLOG_USE_GLOG_EXPORT` 与依赖 include 路径
- **验证**: 补丁后 make 全量编译通过（rc=0）；conan-verify G2 conan create 通过（rc=0）；上游 14 用例全通过
- **适用范围**: 所有在 C++17 下消费 glog 0.7.x 且直接包含 `<glog/logging.h>` 的 C++ 库（尤其老代码先包含 glog 后包含标准容器的源码）；cross-library 可复用
- **四范围查重**: 正式知识 index.tsv **未命中**（grep glog/DECLARE_string/fLS 无条目）；doc/ **未命中**；图谱 engine 查询（"glog flags.h DECLARE_string std::string fLS namespace C++17 include order"）**未找到匹配错误模式**；drafts/ **未命中**（DRAFT-odin-llvm / DRAFT-onnxruntime 为不相关主题的误匹配）

### 候选 2: 上游 CMakeLists cmake_minimum_required(<3.5) 与 CMake 4.x 不兼容

- **真实错误**: `CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed`；conan-verify G2 首次配置失败（reports/conan-create.log，退出码 1）
- **根因**: 上游 CMakeLists.txt 声明 `cmake_minimum_required (VERSION 2.8)`；OHOS SDK CMake 4.1.2 移除 <3.5 兼容策略
- **修复**: 补丁 0001 提升为 `cmake_minimum_required(VERSION 3.5)`（本地直编与 CI 均生效，比仅在 tc.variables 注入更稳）
- **验证**: 补丁后 G2 conan create 通过（rc=0）
- **适用范围**: 所有 cmake_minimum_required(<3.5) 老项目在 CMake≥4 工具链下；cross-library 可复用
- **四范围查重**: 正式知识 **E103（bump-cmake-minimum-version，命中）** + doc/E103.md；图谱命中；草稿 **DRAFT-E321-cmake4-policy-version-minimum（命中，同一问题族）**、**DRAFT-13532-getdns（cmakedeps 相关，部分）**、**DRAFT-cmake4-policy-version-minimum（命中）**

### 候选 3: boost 作为传递依赖时 CMakeDeps 不导出 include 目录，导致公开头含 boost 头的库消费者编译失败

- **真实错误**: conan-verify G2 test_package 编译 `Cassiopee.h:10: fatal error: 'boost/archive/text_oarchive.hpp' file not found`；检查生成器 `boost_INCLUDE_DIRS_RELEASE` 为空（boost/1.90.0.3 包），而 `conan_toolchain.cmake` 的 CMAKE_INCLUDE_PATH 含 boost include
- **根因**: 制品仓 boost/1.90.0.3 的 CMakeDeps 组件（Boost::headers 等）INTERFACE_INCLUDE_DIRECTORIES 为空——include 目录只出现在 CMakeToolchain 的 CMAKE_INCLUDE_PATH（find_path 搜索用），不会自动变成编译 -I；而 cassiopee-c 公开头 Cassiopee.h 直接包含 `<boost/archive/*.hpp>`，消费者编译时必须可见 boost 头
- **修复**: ①依赖改用 boost/1.90.0.4.1（其 CMakeDeps 正确导出 `${boost_PACKAGE_FOLDER_RELEASE}/include`，且含 libboost_serialization.so/libboost_iostreams.so）；②test_package 显式 `self.requires("boost/1.90.0.4.1")`（adql 同款先例）——公开头依赖 boost 的库，消费者 test_package 必须显式声明该传递依赖
- **验证**: 切换 1.90.0.4.1 + test_package 显式 requires 后 G2 conan create 通过（rc=0）
- **适用范围**: 公开头直接包含 boost 头的 C++ 库在 OHOS/Conan 2 + CMakeDeps 下的 test_package；以及依赖版本选择（CMakeDeps include 正确导出的版本）；cross-library 可复用
- **四范围查重**: 正式知识 **E498（headerless library includedirs 清空，方向相反但同属 CMakeDeps include 元数据域，部分相关）**；**E221（CMakeDeps cpp_info 公开契约，相关）**；图谱 E216/E300（CMakeDeps 相关）命中族；drafts/ DRAFT-cmrc / DRAFT-getdns（cmakedeps 相关）部分；无条目描述"传递依赖 CMakeDeps include 空 → 消费者显式 requires"这一具体现象

### 候选 4: 测试二进制 DT_NEEDED 为相对路径（../lib/libcassie.so）运行时 symbol not found

- **真实错误**: ctest 运行 `Error relocating .../test_cassiopee: _ZN13CassieIndexerD1Ev: symbol not found`；LD_LIBRARY_PATH 注入无效
- **根因**: 测试/CLI 二进制 DT_NEEDED 为相对路径 `../lib/libcassie.so`（CMake 构建布局），运行时从源码根（ctest WORKING_DIRECTORY）解析 `源码根/../lib` 不存在；含 `/` 的 NEEDED 不经 LD_LIBRARY_PATH 搜索
- **修复**: 源码根 `lib/` 建立指向 build/lib 的符号链接 + LD_LIBRARY_PATH 注入 boost/glog/gflags/cppunit 库目录（运行时环境恢复，非改上游代码）
- **验证**: 恢复后 ctest 1/1 Passed（rc=0）；test.py exit 0
- **适用范围**: CMake 布局下测试二进制相对 DT_NEEDED 的运行时恢复；cross-library 可复用
- **四范围查重**: 正式知识 **E088（musl namespace 忽略 RUNPATH/LD_LIBRARY_PATH，命中）**、**E004/E078（symbol not found / NEEDED / musl，命中）**、**E298（test_package 缺显式运行环境，命中）**、**E292（relative NEEDED / basename NEEDED 关键词，命中）**；图谱/doc 多条目覆盖

### 噪声项（不入账）
- CassieIndexer 需真实序列文件路径构造（消费者需写输入文件）：库 API 固有语义，非跨库可复用知识 → 噪声，仅在 test_package 与 notes.md 记录
- boost serialization 组件缺失（1.90.0 静态包无 serialization 库）：依赖版本构成差异，由候选 3 的版本选择一并覆盖

## 二、七轴查重

| 轴 | 候选 1（glog <string> 顺序） | 候选 2（CMake 4 策略） | 候选 3（传递依赖 CMakeDeps include 空） | 候选 4（相对 DT_NEEDED） |
|---|---|---|---|---|
| exact_duplicate | false（四范围均未命中） | false（E103 为正式方案，但补丁法 vs -D 注入有实现差异；既有草稿已覆盖本问题族） | false（E498 方向相反；无条目描述消费者显式 requires 补救） | false（E088/E298 为族命中，无单条完全对应） |
| causal_duplicate | false（glog 0.7.x 头文件展开宏依赖标准库前置，无既有条目记录） | true（同一根因：CMake 4.x 移除 <3.5 兼容） | false（根因为特定 boost 包 CMakeDeps include 导出缺失，E498 根因相反） | true（同一根因：含/相对 NEEDED 不经 LD_LIBRARY_PATH） |
| trigger_overlap | false（无既有签名） | true（错误签名同一正则族） | true（INTERFACE_INCLUDE_DIRECTORIES/imported target include 域） | true（Error relocating/symbol not found 同一签名） |
| solution_overlap | false | true（bump 最低版本 / -D 注入同方向） | partial（显式 requires 与 E498 清空 includedirs 均为"修正 CMakeDeps include 元数据"方向，但动作相反） | true（运行时路径注入） |
| combination_novelty | true（glog 头顺序 + C++17 + GLOG_USE_GLOG_EXPORT 三要素组合无既有记录） | false | true（公开头含 boost + 传递依赖 include 空 + 显式 requires 组合无既有记录） | false |
| boundary_novelty | true（适用边界=任意直接含 glog 后置标准容器头的 C++17 源码） | false（既有草稿已表述） | true（边界=依赖包 CMakeDeps include 空时的消费者侧补救） | false |
| test_migration_novelty | false（与测试迁移无关） | false | false | false |

**关系字段**：
- 候选 1: `similar_to` 无；`caused_by` glog 0.7.x flags.h 宏设计 + C++17 libc++；`prerequisite_of` 无；`conflicts_with` 无
- 候选 2: `similar_to` E103、DRAFT-E321-cmake4-policy-version-minimum；`caused_by` CMake 4.x 策略移除；`prerequisite_of` 无；`conflicts_with` 无
- 候选 3: `similar_to` E498、E221、DRAFT-getdns-cmakedeps；`caused_by` boost 包 CMakeDeps include 导出缺失；`prerequisite_of` 无；`conflicts_with` 无
- 候选 4: `similar_to` E088、E004、E078、E298、E292；`caused_by` CMake 相对 DT_NEEDED 布局；`prerequisite_of` 无；`conflicts_with` 无

## 三、路径决定

- **候选 2 与候选 4**: causal/solution/trigger 全轴重叠，被既有正式知识（E103/E088/E004/E078/E298/E292）完整覆盖 → 复用既有知识，不入账为新增。
- **候选 1（glog <string> 前置包含）**: 四范围查重未命中、组合新颖性成立、已验证（本地 make + G2 + 上游 14 用例全过）、可跨库复用 → **`new_draft` 成立，走路径 B**，建立同 stem 的 `.md/.kv` 草稿。
- **候选 3（公开头含 boost 的消费者显式 requires）**: 与 E498 方向相反、无既有条目描述消费者侧补救，组合新颖性成立、已验证（G2 通过）、可跨库复用 → **`new_draft` 成立，并入候选 1 的同一路径 B 草稿集**（两候选均为本轮实测验证的 OHOS Conan/CMake 消费侧知识，合并为一条草稿避免碎片化）。

**决定依据**（knowledge-reuse-governance）: 候选 2/4 完整重复 → 复用原条目走路径 A；候选 1/3 已由本轮真实日志验证、可跨库复用且查重未命中/部分覆盖并存在新增差异 → 路径 B 成立，建立 `DRAFT-cassiopee-c-glog-string-order-and-cmakedeps-consumer-include` 的 .kv/.md 配对草稿。草稿与三方库归档文件（archives/c/cassiopee-c/）进入同一个 PR。
