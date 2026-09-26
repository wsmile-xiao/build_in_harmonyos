# mdm 0.1.3 — HarmonyOS PC 适配笔记

- 上游: https://github.com/cklin/mdm （Middleman Distributed Make，tag `release-0.1.3`）
- 取源: `https://github.com/cklin/mdm/archive/refs/tags/release-0.1.3.tar.gz`
  sha256 `d3dcc78d54e8801077926df44864a8fc537c3a2e29f2489b4fed5e3891a56adf`
  （Debian .orig 19219B 哈希不同——打包元数据差异，SCT 台账已注明；PF7 拉黑池址）
- 构建系统: 裸 Makefile（build() 显式驱动编译器绕开上游的 gcc 链接行假设）
- 源码补丁: 一枚 `patches/0001-mdm-run-fix-unsequenced-execvp.patch`——修
  programs/mdm-run.c 直通模式 `execvp(*argv, ++argv)` 的无序求值 UB（改源码，
  非零补丁方案；见「最终方案」第 2 条）
- 状态: built（本地 conan create 与 W3 本地 CI 真实通过；未 upload ⇒ 不标
  published。取值与版本级 manifest.yaml 的 status 同源，由 finish 判决写入）
  ⚠ 该「真实通过」的实测版次是 `774740e445`（09:09–09:10 那一轮）；W4 整改 r2
  的文本提交（`c5fe567292` 及后继）**未重跑门禁**——设备 inode 准入闸拒绝放行
  （`stat -f` 实测 inode 余 80,882 < 该闸 500,000 下限），细节与影响见
  reports/test-report.md「日志锚点」节。因 conandata 的 patch_description 已改
  ⇒ recipe revision 会变 ⇒ 下一轮必须重跑 conan-verify + finish 再回填读数。
- 交付面: 协调核心三件 mdm-run / mdm-master / mdm-slave（零依赖，纯 libc）
- license: Apache-2.0（LICENSE 原文）

## 症状

1. `make` 直接构建失败：`clang-15: error: cannot specify -o when generating
   multiple output files`——上游链接行 `mdm-% : programs/mdm-%.c $(LIB)` 把
   1 个 .c 与 N 个 .o 一起交给 `$(CC) -o $@ $+`。
2. `mdm-run <cmd> <args…>` 直通模式不可靠：上游写作 `execvp(*argv, ++argv)`，
   clang 报 `-Wunsequenced`（同一表达式里无序读写 argv）——求值顺序不同，被
   exec 的程序名会在「mdm-run 自身」与「用户命令」之间错位。
3. mdm-top 链接需要 `-lcurses`（ncurses 监控 UI，唯一的 curses 依赖面）。
4. 上游 `override CC := $(shell which mdm-run ...)` 在 PATH 恰有 mdm-run 时
   把编译命令包进 mdm-run（分布式编译机制）。

## 根因

1. Makefile 是 **gcc 假设**：gcc 接受「1 个 .c + N 个 .o + -o」的编链合一，
   clang 15 一律拒绝 `-o` 搭配多输入。clang 的约束下该规则不可用。
2. `*argv` 与 `++argv` 之间没有序列点，属 C 标准意义上的未定义行为；上游只
   在「某个求值顺序恰好符合直觉」的编译器上表现正常，不是可移植语义。
3. mdm-top 之外的三件核心程序都是纯 libc（buffer/comms/socket/hazard/procfs
   五个库单元 + 三个 main），无 curses 依赖。
4. install 目标烧死 `/usr/bin/install`、`/bin/sed`、`/bin/gzip` 并改写
   `/etc` 类路径——发行版打包逻辑，不属于配方职责。

## 最小复现

```sh
make mdm-run CC=clang   # → clang-15: error: cannot specify -o when generating
                        #    multiple output files
```

## 已试过的失败方案（防重复踩）

1. **直接 `make mdm-run mdm-master mdm-slave CC=clang`**：如上 clang 拒绝
   链接行。不要试图靠 make 变量绕（`override CFLAGS +=` 会强制追加，但
   链接行的多输入结构不变）。
2. **期望 make 内置规则先编 .o**：链接行在 .o 尚不存在时也会先执行
   （prerequisite 图解析顺序），错误依旧。
3. **绕开 exec UB 而不打补丁**（早期迭代的做法）：改测试形态、用 toybox 多路
   复用器按 argv[0] 分发的特性去凑语义。能跑，但把上游缺陷转嫁成消费者约束，
   且依赖被执行程序的内部分发约定 ⇒ 已废弃，改为下面的 0001 补丁。
4. **修 ncurses 链接名以保留 mdm-top**：ncurses 制品包提供 libcurses 还是
   libncurses 未验证，mdm-top 是唯一 curses 消费者且为可选监控 UI ⇒
   裁剪并披露，不为它引入未验证依赖面。

## 最终方案

1. **build() 显式驱动编译器**（subprocess，不走 make）：
   - 编译 8 个翻译单元：`clang -O2 -Wall -D_GNU_SOURCE -Iinclude -c ...`
     （CFLAGS 对齐上游 override 行；编译器 R33 从 conan conf 注入；R9 串行）
   - 链接 3 个二进制（成员清单对齐上游规则）：mdm-run（run.o+buffer+comms+
     socket）、mdm-master（+hazard.o）、mdm-slave（slave.o+buffer+comms+socket）
   - 注：`library/procfs.c` 属编译超集（对齐上游 $(LIB) 全量），三个核心均未
     链接 procfs.o，无害。
2. **补丁 0001 修 exec UB**：`execvp(*argv, ++argv)` → 拆出
   `char **args = argv + 1;` 后 `execvp(args[0], args)`（错误信息随之改读
   `args[0]`）。语义 = 确定性 exec 用户命令、参数向量自该命令起，等价于 gcc
   下的实际行为与作者意图；单 hunk、无平台宏（R8 合规）。修复后 G2 构建日志
   内 `unsequenced` 一词仅命中补丁文件名，无编译告警。
   - **补丁类型口径（W4 审计 r1 的 P3 项）**：conandata.yml 记
     `patch_type: bugfix`，而 code_style 第 12/13 条示例给的是 portability——
     属风格偏差非缺陷：本补丁修的是 C 标准意义上的未定义行为（clang 实测
     -Wunsequenced），不是「为平台移植而新加的开关」，按语义保留 bugfix；
     W3 已按 bugfix 正常应用（见构建日志 `Apply patch (bugfix):` 行）。
     不为风格牵动补丁内容，也不因此动 hunk。
   - **补丁文件的可改性纪律（W4 整改 r2）**：hunk 内容（首个 `--- ` 行起到
     文件末）按「一个字节都不许变」冻结，以免改注释牵动代码行、使已验证的
     构建产物与盘上源码脱钩。因此 hunk 内写进 programs/mdm-run.c 的两句英文
     注释（措辞方向与本条相反且互相否定）**冻结保留**，权威表述以补丁文件
     顶部位于 diff 之前的 `#` 说明块（patch_ng 解析时忽略、不改代码）与本
     文件、conandata.yml、版本级 manifest.yaml 的同义口径为准。已实测：加说明
     块前后 patch 后的 programs/mdm-run.c sha256 相同。
3. **裁剪披露**：mdm-top（ncurses 监控器）不构建不交付；mdm.screen/ncpus
   脚本不属二进制交付面。
4. **打包**：package() 自拷三件到 bin/、LICENSE 入 licenses/；
   commands.json 声明工具面（R38：文件在**软件级** archives/m/mdm/ 下）。
   license 定案 Apache-2.0（LICENSE 原文）。
5. **测试面**：上游 0 测试（清点证据 `reports/upstream-test-scan.txt`；24 处
   assert 命中为源码内 libc 防御性断言非测试框架）。test_package 新增 9 条
   消费者断言：
   - A 产物面 5 条：mdm-run/mdm-master/mdm-slave 存在且可执行（循环 3 条）、
     mdm-run ELF magic 1 条、包内无 mdm-top（裁剪校验）1 条；
   - B 功能面 4 条：`mdm-run /bin/sh -c "echo mdm-hello"` 真实 exec rc=0、
     该命令 stdout 透传（grep mdm-hello）、无命令参数时 rc≠0（实测 rc=1，
     拒绝静默空跑）、子进程退出码透传（`/bin/sh -c "exit 3"` → rc=3）。
   - 被测 exec 一律绝对路径 `/bin/sh`：conanrun 环境 PATH 不含系统目录，
     绝对路径不走 PATH 查找 ⇒ 断言与 PATH 无关。

## 适用边界

1. **mdm-top 未交付**：需要 curses 生态（ncurses 包的 curses 链接名兼容性
   未验证）。需要监控 UI 的场景待 curses 面补齐后另行扩展。
2. **mdm-run 的 exec 语义经补丁修正**：上游 `execvp(*argv, ++argv)` 属无序
   求值 UB，本包以 0001 确定性化为 `execvp(args[0], args)`（args = argv + 1）
   ⇒ `mdm-run <cmd> <args…>` 稳定 exec `<cmd>` 并把 `<args…>` 交给它。这是对
   上游源码的修改，不是上游原行为；上游若将来自行修复，本补丁应随之退役。
3. **分布式编译依赖 hostname/socket 面**：mdm-run→master→slave 的协调链路
   走 unix socket（library/socket.c），单机 smoke 已覆盖 exec 透传；跨机
   协调需要 ssh 通道（mdm.screen 脚本），不在本包测试面内。

## 测试数字口径

- 上游测试: 0（`upstream_tests_exist: false`，证据 `reports/upstream-test-scan.txt`）
- 新增消费者断言: 9 条（test_package/test.sh，真执行打包二进制）
- 本机直编验证（结构性事实，逐条可在盘上复核）: 本包的编译/链接面是配方里的
  显式清单——`conanfile.py` 的 COMPILE 清单恰 8 项（第 31-35 行：buffer/comms/
  socket/hazard/procfs 五个库单元 + run/master/slave 三个 main）、LINK 恰 3 项
  （第 36-43 行的三个键 mdm-run / mdm-master / mdm-slave）；build() 对 COMPILE
  逐项 `-c`、对 LINK 逐项链接并逐个断言产物存在（第 98-106 行）。
  打包面唯一串 `package(): Packaged 4 files: mdm-run, mdm-master, mdm-slave,
  LICENSE` 在 `reports/w3-local-ci.log:188` 与 `reports/conan-create.log:115`
  各出现一次。W4 审计 r1 指出旧写法
  「8/8 翻译单元、3/3 链接」在五枚证据件（w3-local-ci.log、conan-create.log、
  conan-verify-report.md、test-report.md、upstream-test-scan.txt）里没有对应
  计数体 ⇒ 改述为上述可在
  盘上数出来的结构事实，不再引用不存在的读数。
- 执行归属与时序（2026-09-26，设备 A 机）: 配方与 test_package 由 主理-61 起草
  并推送 `5c032f5b80`（07:25）；W4 审计 r1 的 P1x3+P2 整改（含 R38 commands.json
  归位到软件级 archives/m/mdm/）与 W3 转绿由 主理-66 完成（`e6fa23e92a` 09:03、
  `774740e445` 09:12）；本轮 W4 整改 r2 由 主理-66 窗的执行棒 棒-66d 完成。被引
  证据路径全部位于 `~/qzy/主理-66-mdm-0.1.3`（主理-66 名下 worktree），执行时刻
  与绑定 HEAD 见 reports/test-report.md。
- 正式门禁读数以本次 conan-verify / CI 判决为准，PR 正文数字与之一致。
---

**编译结束**: 2026-09-26 09:09
**最终状态**: built
