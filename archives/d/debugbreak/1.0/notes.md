# debugbreak 1.0 适配笔记

## 编译环境
- 构建系统: makefile（上游 GNUmakefile，无 configure；header-only 库）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤

debugbreak 1.0 是单头文件库（debugbreak.h + debugbreak-gdb.py 辅助脚本 + 4 个 gdb 驱动的
测试程序）。无需 configure，配方（conanfile.py）为 header-only 形态：

1. `ohc-run.py init-build debugbreak 1.0 --url <官方 v1.0 tarball>` — 下载官方源码
   （SHA-256 62089680cc...ae2f），初始化归档骨架与 `.build-context-debugbreak-1.0`。
2. 语言预检（lang-preflight）：工具初判 mixed → env_unsupported，经人工按协议 D.4
   边界规则复核为误判（GNUmakefile 未被识别为 Makefile；debugbreak-gdb.py 属辅助脚本
   不应计入主体；C/C++ 兼容族），覆盖判定继续适配，详见下方问题表。
3. 适配编译验证：`make`（clang -Os -Wall）编译 4 个上游测试程序全部通过；4 程序直接
   运行均以 exit=133 (SIGTRAP) 验证陷阱指令实际触发。
4. Conan 配方：conanfile.py（header-library，build() 内编译上游 4 测试程序作适配检查，
   package() 打包 include/debugbreak.h + share/debugbreak/debugbreak-gdb.py +
   licenses/COPYING）；conandata.yml 官方 URL + 实测 SHA-256；test_package 消费者测试
   （test.c）+ 鸿蒙专项测试（test_ohos.c，编译期平台选择断言 + 运行期 SIGTRAP 验证）。
5. `conan create`（ohos-aarch64 profile）验证通过：G0-G4 门禁、test_package 2/2 用例
   通过（test_debugbreak + test_ohos）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 判 mixed → env_unsupported | 工具仅识别名为 `Makefile` 的构建系统文件，`GNUmakefile` 未命中 → build_system=none；且 debugbreak-gdb.py（gdb 辅助脚本）被计入主体统计 → c:3/py:1/cpp:1 主体占比 60% < 70% | 按协议 §D.4 边界规则复核：辅助脚本不算主体、C/C++ 混编按主体判非 mixed、c↔cpp 兼容族不迁移 → 判 cpp，继续适配（最终回报附完整证据） |
| 2 | GitHub 直连不可达（github.com:443 超时） | 本机网络无法直连 GitHub | conan create 本地验证时临时将下载 URL 指向 ghfast.top 镜像（CI 同款镜像兜底，R39），验证后立即还原为官方 URL；conandata.yml 提交内容保持官方 HTTPS + SHA-256 |
| 3 | gdb 驱动上游测试失败：`ptrace: Permission denied` | HarmonyOS PC 限制 ptrace，gdb 无法跟踪子进程 | 记录为真实平台阻塞（非库缺陷）；用进程内 SIGTRAP 信号处理器 + longjmp 等价验证陷阱触发（test_package/test.c 与 test_ohos.c），4 上游程序直接运行均 exit=133 确认 brk 触发 |
| 4 | test-debugbreak.gdb 报 `Undefined command: "import"` | 本机 gdb 16.3 构建时未启用 Python，debugbreak-gdb.py 扩展无法加载 | 记录为工具链配置限制；C++ 用例改用直接运行验证（SIGTRAP 触发） |
| 5 | test_package/build/ 生成物含本地路径 | conan create 在 test_package 内生成了 build 目录 | 清理生成物，确保归档只含配方与源码文件；最终提交前复扫 file://、缓存路径、currentUser 等污染标记 |

## 源码修改

无。header-only 库，未改动上游任何文件，无 patches/。

## 依赖版本

无三方依赖（仅 OHOS libc 与编译器内建头）。conanfile.py 无 requires/tool_requires。
工具链：clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）、GNU Make 4.4.1、
CMake 4.1.2、conan 2.32.0（OHOS 适配版）、gdb 16.3（无 Python）。
---

**编译结束**: 2026-09-06 22:47
**最终状态**: published
