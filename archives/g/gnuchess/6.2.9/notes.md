# gnuchess 6.2.9 适配笔记

## 编译环境
- 构建系统: autotools (autoconf 2.69 生成的 configure 随 tarball 分发)
- 编译日期: 2026-09-15
- 编译器: clang/clang++ (OHOS aarch64, 经 conanbuild 环境注入)
- 状态: built

## 编译步骤

1. W0: 上游依赖检查 — configure.ac 的依赖探针全部位于可选 readline 分支内
   (AC_CHECK_LIB(ncurses/readline), configure.ac:38-41)，引擎主体零依赖；
   制品仓 readline/8.3、ncurses/6.4-6.6 均已发布（已实测）。
2. 语言预检 lang-preflight: cpp (源文件 82 个 100% cpp) 通过。
3. 上游测试清点: 无 tests/ 目录；全部 Makefile.am 无 TESTS/check_PROGRAMS/
   dejagnu 注册 → N_static=0（证据见 test_package/MANIFEST.yml）。
4. conan-init 生成骨架后定制配方；conan-verify G2 真实构建。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 的 confXXXXXX 临时目录 Permission denied（E011/E114 已知墙） | HMDFS 对 `umask 077 && mktemp -d` 创建的目录强制 setgid/0700，UID 映射后进程不可写 | build() 中对 configure 调用 _drop_umask_077（opendmarc/ekg2 同款） |
| 2 | readline 探针必败 | configure 硬编码 AC_CHECK_LIB(ncurses,...)，而 conan ncurses 只发 libncursesw.a；探针失败 → readline 关闭 | 显式 --without-readline（引擎功能不受影响，readline 仅交互行编辑） |
| 3 | config.sub 不识别 ohos 三元组 | autoconf 2.69 (2015) 早于 OHOS | 手动 configure 只传 --build=aarch64-unknown-linux-gnu，不传 --host（GLM-19 pit #1/dominion 同款） |
| 4 | components.cc:174 error: use of undeclared identifier 'pthread_cancel' | OHOS musl 不提供 pthread_cancel（components.cc 唯一一处，用于 quit 时停止 stdin 线程） | cancel+join 改为 pthread_detach：输入线程随 EOF/quit 自然退出，进程退出回收 |

## 源码修改

无补丁文件（patches 为空）。configure 的 umask 077 修改在 build() 内以
受控字符串替换完成（E011/E114 rec_approach: edit-umask-in-configure）。

## 依赖版本

无 conan 依赖（--without-readline 后引擎零依赖）。

## 验证结果

- conan-verify G2: conan create 干净构建通过（结果以 .ci-result.json 为准）
- 消费者测试: test_gnuchess.sh — 3 个可执行齐备 + 引擎真实对局断言
  （`go depth 3` → 引擎输出 "My move is"，src/frontend/engine.cc:316 确定性行为）

## 注意事项

- 上游静态测试 N_static=0：无上游套件可执行，消费者测试补位（R51 三步法）。
- gnuchessu/gnuchessx 是 shell 包装脚本（UCI/XBoard 模式），非二进制。

### 对话 #1 (2026-09-15, GLM-34)

- 从 conan-init 骨架起完成全流程适配：语言预检 cpp 100%、上游测试清点
  N_static=0、E011/E114 umask 修复、--build-only 交叉、--without-readline、
  pthread_cancel→pthread_detach、消费者测试真机断言引擎出招（My move is），
  conan-verify G2 真实构建通过。
---

**编译结束**: 2026-09-15 02:49
**最终状态**: built
