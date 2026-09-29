# ksyntaxhighlighting 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake（KDE ECM 工程）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4（OHOS SDK）
- 状态: built（conan-verify G0-G4 全通过，待 CI 发布后置 published）
- 分支: feat/ksyntaxhighlighting-6.26.0

## 依赖
- qtbase/6.11.1（Qt6 Core/Network/Gui）
- ecm/6.26.0（tool_requires）
- perl/5.42.2（tool_requires，上游源码用 Perl 生成器）

## 配方关键点
- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单
- `KF_SKIP_PO_PROCESSING=ON` + 补丁跳过 `ecm_install_po_files_as_qm(poqm)`（无 Qt Linguist 工具链）
- `BUILD_EXAMPLES=OFF` + 补丁添加 BUILD_EXAMPLES option（库打包不需要 examples）
- `QRC_SYNTAX=ON`：语法定义内嵌 QRC，消费者无需外部数据文件
- `BUILD_TESTING=ON`：上游 6 个 CTest 全量执行
- `_library_runtime_env()` 对 OHOS prepend `/system/lib64`（libc++_shared.so 遮蔽修复）
- katehighlightingindexer.cpp 使用 `std::strong_ordering`（C++20），而 profile `compiler.cppstd=17` 作为普通变量在 conan_toolchain.cmake 中遮蔽了 CACHE 写入的 20 → 通过 CMakeLists 补丁强制 `set(CMAKE_CXX_STANDARD 20)`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create 中 /data/service/hnp/bin/cmake 运行报 libc++ 符号重定位失败（_ZNKSt4__n119__shared_weak_count... symbol not found） | 沙箱 LD_LIBRARY_PATH 中不兼容的 libc++_shared.so 遮蔽了兼容版本 | `_library_runtime_env()` 对 OHOS prepend `/system/lib64`（ksanecore/kconfig/kcrash/kio 6.26.0 先例） |
| 2 | katehighlightingindexer.cpp:3236 `std::strong_ordering` 编译失败 | profile cppstd=17 普通变量遮蔽 conanfile CACHE 写入 20 | CMakeLists.txt 补丁中强制 `set(CMAKE_CXX_STANDARD 20)` + `CMAKE_CXX_STANDARD_REQUIRED ON` |
| 3 | test_package cmake.configure() 报 libc++_shared.so 加载失败 | test_package 构建阶段同样被不兼容 libc++ 遮蔽 | test_package 增加 `_libcxx_env()` prepend `/system/lib64`，build() 与 test() 均应用 |
| 4 | 6.18.0 旧补丁行号与 6.26.0 源码不匹配 | 上游 6.26.0 CMakeLists 结构调整 | 在 .work 源码重新修改后用 refresh-patch --auto 生成新补丁 |
| 5 | conan-verify 缓存复用（Already installed）导致验证失真 | 先前失败构建残留缓存二进制 | conan remove 清理 5 个历史 recipe revision 后强制重新干净构建验证 |

## 测试
- 上游 CTest：**6/6 通过**（wildcardmatcher_test, repository_test, theme_test, testhighlighter_test, htmlhighlighter_test, folding_test）
- highlighter_benchmark / repository_benchmark：BENCHMARK 配置，常规 CTest 不注册
- test_package：消费者链接 KF6::SyntaxHighlighting，加载内嵌 C++ 语法与 Breeze Light 主题 → PASS

## 交付物
- conanfile.py、conandata.yml、manifest.yaml、notes.md、test_package/、patches/0001-CMakeLists.txt.patch

## 知识候选（最终结论）
- 候选 A（KDE tarball utils/*/pyproject.toml 导致 lang-preflight 误判 python）→ **REUSED_EXISTING**：复用 DRAFT-bptree-lang-preflight-pyproject-tooling-false-positive（同根因：lang_detect 对任意 pyproject.toml 直接判 python；本包为 KDE 辅助工具场景复现）
- 候选 B（profile cppstd=17 普通变量遮蔽 recipe CACHE CMAKE_CXX_STANDARD=20 → CMakeLists 补丁强制项目标准）→ **REUSED_EXISTING**：E096 显式设置 CMAKE_CXX_STANDARD 方案族（本包以 CMakeLists 补丁落地）
- 候选 C（conan 沙箱 libc++_shared.so 遮蔽宿主 cmake/qtpaths 符号重定位 → LD_LIBRARY_PATH prepend /system/lib64）→ **DRAFT_READY**：新草稿 E657-draft-DAE2 已创建并验证（graph validate 通过、draft-review 完成、verification_cmd 真实执行 conan create PASS）

## 对话记录
- 任务切换：原 skanlite 任务切换为 ruqola 2.8.1 适配；ksyntaxhighlighting 是 ruqola 的 KF6 REQUIRED 依赖（制品仓仅 6.18.0 < 6.22.0 要求），本包作为依赖项适配
- conan-verify 全 PASS 后完成本轮记录
- W4 审计 verdict=pass，4 条非阻塞问题全部修复（notes.md 状态统一为 built；manifest 绝对路径字段保留为补丁生成溯源元数据；E657 source_pr/source_commit 待 PR 合并后回填）

**编译结束**: 2026-09-28
**最终状态**: built（待 CI 发布后置 published）
