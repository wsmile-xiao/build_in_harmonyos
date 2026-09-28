# lprng 3.8.b 适配笔记

## 编译环境
- 构建系统: autotools（configure + Automake Makefile.in）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4（/data/service/hnp/bin）
- 状态: built（conan-verify G0-G3 全绿；W3 本地 CI 模拟通过）

## 编译步骤
1. init-build 取源：官方上游发布件
   https://downloads.sourceforge.net/project/lprng/lprng/LPRng-3.8.B/LPRng-3.8.B.tar.gz
   sha256=541346a4bccd45acdeff1a8d09e80cc6a8bd22f9088739628ba787924a1806d1
   （与 Debian sid Sources 索引 .orig 同值同长度，B 机自算复核同值）
2. configure（VPATH）：--disable-ssl --disable-nls CFLAGS=-fcommon
   （kerberos/tcp-wrappers 上游默认关闭，无需显式开关）
3. make -j2 全绿，8 个程序：lpr lpq lprm lpstat lpc checkpc lprng_certs lprng_index_certs
4. conan 配方自含三类 OHOS 修复（见下表 2/4/5），conan create 干净构建 + test_package 断言 14/14 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 框架 init-build 直接崩 NameError | ohc/check_env.py:33 except 分支引用未绑定的 e；触发源是 B 机 usr/local/bin/automake 的 shebang 指向不存在的 usr/local/bin/perl | 不改框架（须单独 PR）：会话级 PATH 垫片 automake 转由 hnp perl 执行，探针真实运行 |
| 2 | configure/config.status 声称 creating 全部文件但盘上一个没有，rc=0 | B 机 HMDFS：属主-only 模式（0700：toybox mkdtemp、umask 077 mkdir）建出的目录 ACL 天生损坏，属主自己也写不进，chmod 不可修复；config.status 经 confXXXX 临时目录 mv 落盘全部静默失败 | 配方内 mktemp 垫片：mktemp -d 后换全新名字 mkdir -m 755 重建并写探针验证（E528 式 recipe-local env closure，libunwind 1.6.2 同型） |
| 3 | 链接期 checkpc/lpd 多重定义错误 | clang 15 默认 -fno-common，LPRng 3.8.B(2003) 在 lp.h 定义全局变量 | CFLAGS=-fcommon（经 manifest configure_options 传导到框架 Step3 与 conan 配方） |
| 4 | make install 报 install: inaccessible or not found | OHOS 无 install 程序（coreutils 装的是 ginstall） | 配方内 install 垫片：有序 fallback 链 install→ginstall→busybox install→toybox install→纯 sh 替身（逐候选探测、回退链逐级日志；候选 install 走 PATH 逐目录扫描并跳过垫片自身目录——PATH 前缀使 command -v 命中垫片自己，exec 自身即无限自递归 busy-spin，G2 实证 2026-09-28；sh 替身覆盖 -c 与 -c -m MODE 两种调用形态）|
| 5 | install-exec-hook 的 ln 硬链接 Operation not permitted | HMDFS 不支持硬链接（与预扫描 PSCAN-HMDFS-001 符号链接限制同族） | 配方内 ln 垫片：ln 转 cp（lp/cancel 由拷贝产生） |
| 6 | conan create 里 configure 产物同样蒸发；install 打到只读根 | conan 2 工具链默认 --prefix=/，且 generate 里 save_script 不进 conanbuild 聚合 | 内联 PATH=ohc-wrappers 前缀手工跑 configure/make/install（libunwind 1.6.2 模式）+ make install DESTDIR=package_folder |
| 7 | L1 判 negative test: test does not depend on package | test_package 的 can_run 门在独立 conan test 下为 False，test() 体被静默跳过，R34 破坏性反向验证 rc=0 被判假测试 | 去 can_run 门：无条件运行消费者断言（CI 本就在真机执行）；破坏验证时断言必然失败退 1 |
| 8 | W3 L0k R38：CLI 软件缺 commands.json | 软件级目录缺该文件 | 补 archives/l/lprng/commands.json |

## 源码修改
无补丁（patches_applied=[]）。全部适配在配方层：三垫片（mktemp/install/ln）+ configure 旗标 + -fcommon。

## 依赖版本
无 conan 依赖（dependencies=[]）。ssl/kerberos/tcp-wrappers/nls 均关闭。

## 验证结果

```bash
conan-verify: G0 PASS / G1 PASS / G2 PASS（conan create 干净构建 + test_package）/ G3 PASS
make -j2: RC=0（VPATH）；W3 本地 CI: L0 pass, L1 pass(含 R34 阴性验证), L4 pass, L5 pass
五维账本: 上游用例总数=0 执行=0 通过=0 失败=0 跳过=0
消费者断言数=14（8 二进制存在可执行 + etc 两份样例配置 + 4 客户端非空输出执行证明）→ 14/14 通过
```

- 顶层 Makefile 无 check 目标：make check 退出 2（No rule to make target check）；
  全树无 TESTS/check_PROGRAMS/add_test；TESTSUPPORT 目录上游从未随包
  （Makefile.am 第 2 行注释 still to include: TESTSUPPORT 自证）。

## 交付物
conan 包 lprng/3.8.b（application）：bin/ 8 程序 + etc/lpd/lpd.perms.sample + etc/printcap.sample + licenses/LICENSE

## 注意事项
- 任务串 3.8.b（小写）与上游 tarball 实名 LPRng-3.8.B（大写）不同源字符；全程未归一化：
  Conan ref/归档目录/分支按任务串，URL 与解包目录内保留上游大写实名。
- 框架 Step8 的 --version 探测对 4 客户端报失败（EXCLUDE_LIST 留证）：LPRng 3.8.B 为老式 getopt
  无 --version 长旗标；二进制本体为合法 aarch64 ELF 且可执行。
- reports/test-report.md 的 FAIL 即上游无 make check 目标的事实留证（rc=2）。
- reports/w3-local-ci.log、conan-create.log、test-report.md 三件已自 PR 撤下
  （review-memory 文件规范第 19 条：PR 禁止 *.log/test-report）：设备侧留证、
  判决行原文引注于本文件与 conan-verify-report.md。
- 可升知识库：HMDFS 0700 目录 ACL 缺陷与 mktemp/ln/install 三垫片配方模式；
  R34 阴性验证要求 test_package 不带 can_run 门。
---

**编译结束**: 2026-09-28 04:33
**最终状态**: built
