# ksyntax-highlighting 5.116.0 适配笔记

KDE Frameworks 5 语法高亮引擎（KF5/Qt5），构建产物 `libKF5SyntaxHighlighting`。

## 编译环境

- 构建系统: CMake（KDE Frameworks 标准 KDECMakeSettings/ECM 模块）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (aarch64-linux-ohos) / clang++ (libc++17)
- 状态: built（本地 conan create 通过，CTest 6/6 全过）

## 编译步骤

由 Conan 配方驱动（`archives/k/ksyntax-highlighting/5.116.0/conanfile.py`）：

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

配方内部：
1. `CMakeDeps` 重建聚合 `Qt5Config`（qt5-qtbase 只发布各 per-module config）
2. `CMakeToolchain` 注入平台适配变量（见下）
3. `cmake.configure()` → `cmake.build()` → 上游 CTest 全量执行

## 平台适配要点

| 配置 | 值 | 说明 |
|------|-----|------|
| QT_MAJOR_VERSION | 5 | 指向 Qt5（qt5-qtbase/5.15.2.2） |
| KF_IGNORE_PLATFORM_CHECK | TRUE | OHOS 不在 KDE 平台列表，跳过平台检测 |
| KF_SKIP_PO_PROCESSING | ON | ECMPoQmTools 声明原生支持，跳过 po 翻译（无需补丁，区别于 KF6 6.18） |
| QRC_SYNTAX | ON | 将语法/主题定义 bundle 进库内资源，消费者无需外部数据文件 |
| BUILD_QCH | OFF | 跳过 API 文档（QCH）生成 |
| KSYNTAXHIGHLIGHTING_USE_GUI | ON | 启用 Qt5::Gui 依赖（核心库公共依赖） |
| CMAKE_AUTOMOC/AUTORCC | qt5-qtbase bin/moc、bin/rcc | CMakeDeps 不导出 Qt5::moc/rcc，手动指定 |
| PERL_EXECUTABLE | perl/5.42.2 bin/perl | data/generators/*.pl 生成 PHP 语法定义（REQUIRED 工具） |
| ECM_MODULE_PATH | ecm/6.26.0 share/ECM | ECM 的 CMakeDeps 不传播 ECM_MODULE_PATH，手动设置 |
| SONAME 标志 | `-Wl,-soname,` + NO_VERSIONED_SONAME | OHOS 未映射 Linux CMake 平台，.so 缺 DT_SONAME |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight(R47) 判定 env_unsupported | 检测器用 rglob 递归扫描 basename，把测试夹具 `autotests/input/build.gradle` 与随附工具 `utils/schema-converter/setup.py` 误当语言 manifest（先报 python 后报 java） | 复核为误判：顶层 CMakeLists `project(KSyntaxHighlighting)` + 41 cpp 源码统计；用户确认按 C++ 路径A 继续（误判终态由后续草稿/最终 result 自然覆盖） |
| 2 | W3（finish step5）JC6 拦截"涉及 9 个软件包" | 本地 `origin/main` ref 过期，`git diff origin/main...HEAD` 三基点把中途合入的 9 个 lib 包误算为变更；且本分支无提交→回退 full 整仓扫描误拦 upstream 历史遗留隐藏文件(cloog/kics) | 刷新 `origin/main`/`main` ref 至与 HEAD 同步；以 `JUNK_PR_DIFF` 走 prdiff 模式（与 CI PR 校验一致，仅 8 个本包文件）→ 通过 |
| 3 | test_package `find_package(KF5SyntaxHighlighting)` 找不到 Config | 主包 `cmake_find_mode=none`，CMakeDeps 不生成包装 Config；且其 `find_dependency(Qt5Core)` 用旧式模块名 | test_package `_write_cmake_paths` 把主包 + qtbase 的 `lib/cmake` 加入 CMAKE_PREFIX_PATH（与主配方同模式） |

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | require（Core/Network/Test/Gui） |
| ecm | 6.26.0 | tool_requires |
| perl | 5.42.2 | tool_requires |

全部已在 ohpcd 制品仓发布（R36 通过）。

## 验证结果

```bash
# 上游 CTest 6/6 全过（build() 内 exec，CTEST_PARALLEL_LEVEL=1, timeout 240）
1/6 wildcardmatcher_test  Passed  0.12s
2/6 repository_test       Passed  1.06s
3/6 theme_test            Passed  0.42s
4/6 testhighlighter_test  Passed  1.73s
5/6 htmlhighlighter_test  Passed  2.65s
6/6 folding_test          Passed  1.66s
# → 100% tests passed, 0 tests failed out of 6（Total Test time 7.65s）

# 消费者用例（test_package，调真实公开 API）
$ ./test_ksyntax_highlighting
PASS: KSyntaxHighlighting loaded C++ with Breeze Light

# conan create exit=0；conan-verify 8 道门禁全 PASS
```

> highlighter_benchmark / repository_benchmark 为上游 BENCHMARK 配置测试，默认不注册，不参与常规 CTest。

## 注意事项

- 本机为 aarch64 HarmonyOS 真机（HK 1.12 kernel），host==target 同架构，moc/rcc/katehighlightingindexer 均可用目标二进制原生运行，无需 KF5_HOST_TOOLING（若 CI 为 x86_64 host 交叉到 arm64 target，则需按 src/indexer/CMakeLists.txt 走 host 工具联编）。
- CMake 对 "System is unknown to cmake" 仅告警不阻塞（G0 E092 已知风险已在配方处理）。
- `CMAKE_BUILD_RPATH=$ORIGIN` 未设置（主包通过 Conan 管理 RPATH），test_package 在运行前将依赖库复制到测试镜像目录以解决加载器查找。
