# wdiff 1.2.3 适配笔记（GLM-25，2026-09-13/14）

## 任务信息
- 平台任务号 13413，活动=开源鸿蒙PC专项积分赛-依赖
- 分支 feat/wdiff-1.2.3，worktree ~/qzy/GLM-25-wdiff-1.2.3
- 上游 https://ftp.gnu.org/gnu/wdiff/wdiff-1.2.3.tar.gz
  sha256=29a4457eb0ed35c902e6732d71f25e1d6c7fe7fa0eda0fb6c371ed6779b49fd6

## 适配决策
1. 包类型 application（bin/wdiff），按 R38 声明软件级 commands.json；
   实验性程序 mdiff/unify 保持上游默认（configure 不开 EXPERIMENTAL_PROGRAMS）。
2. `--disable-nls`：AM_GNU_GETTEXT(external)，OHOS/musl 无 libintl（知识 E027）。
3. 显式三元组 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`：
   2014 年版 config.guess 遇 HongMeng 内核报 cannot guess build type。
4. 补丁 0002（configure umask 077→022）：HMDFS setgid 使 mktemp 目录 drwx--S--- 不可写，
   config.status 报 could not setup config files machinery（知识 E011/E114，方法=改 022）。
5. 补丁 0001（src/Makefile.in AM_CPPFLAGS 加 -I../lib）：上游 out-of-tree 构建缺陷，
   gnulib 生成的 error.h 落在构建目录 lib/，src 编译只含 -I$(top_srcdir)/lib 找不到。
6. build() 内把 tarball 预生成的 doc/wdiff.info 复制进构建目录并 utime 置新、
   将 doc/{wdiff.texi,stamp-vti,version.texi} 时间戳按依赖序 pin 旧：
   automake 将 wdiff.info 视为构建产物（DISTCLEANFILES），vti 链每次刷新 version.texi，
   会触发 makeinfo 重建（OHOS 无 makeinfo）。conan.tools.files.copy 保留源 mtime，
   故 copy 后需对构建目录副本再 utime。
7. 消费者测试 test.sh：真实执行 wdiff 二进制断言行为（版本输出、词级 diff
   {+brave+} 插入标记、diff 风格退出码 1、相同文件退出 0）。注意 wdiff 退出码
   语义与 diff 相同（1=有差异），set -e 下需显式捕获。

## 上游测试账本（四维）
- N_static = 4（tests/testsuite，`./testsuite -l` 权威列出：output formats /
  report bad diff binary / use pager / diff as input）
- N_executed = 4（设备真机 in-tree 构建 + make check，全部实跑）
- 通过 3 / 跳过 1 / 失败 0：
  - use pager skipped：测试内 `screen -D -m` 依赖 GNU screen，OHOS 设备无该程序，
    AT_SKIP_IF([test ! -f screenlog.0]) 触发，属环境限制而非适配缺陷。
- N_consumer = 1（test_package/test.sh，4 处行为断言）
- 运行证据：~/tmp/uc2/wdiff-1.2.3/uptest/check.log

## 知识调用与路径 B 判断
- 调用知识：E027（--disable-nls）、E011/E114（umask/HMDFS）、E528 参照、a52dec 归档
  配方骨架（补丁式 umask 修复先例）。
- 查重：知识库无 wdiff 特有条目；本次踩坑（out-of-tree gnulib 头路径、
  automake vti 链+makeinfo 缺失组合）已有 E103/E011 族覆盖大方向，
  细节差异属单库上游缺陷，不构成可跨库复用的新知识 → **不走路径 B**。
---

**编译结束**: 2026-09-14 01:52
**最终状态**: built
