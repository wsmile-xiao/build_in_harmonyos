# smstools 3.1.21 适配笔记

## 编译环境
- 构建系统: makefile（上游为纯 Makefile，无 configure / 无自动生成工具）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（OHOS 工具链，默认目标 aarch64-unknown-linux-ohos）
- 源码: https://smstools3.kekekasvi.com/packages/smstools3-3.1.21.tar.gz
  sha256 a26ba4c02b16f6cf13177bffca6c9230dc5fefaeba8e3030cd4e4905f6a92084（356548 字节，官方源实测 HTTP 200）
- 任务号: 10742（依赖活动）；分支 feat/smstools-3.1.21

## 编译步骤

上游只有两级 Makefile：顶层 `compile:` 转发到 `src/`，`src/Makefile` 的 `all: smsd`
从 14 个 .c 直接编链出单个可执行文件 `smsd`（无库产物、无 install 规则可用于打包，
顶层 `install:` 会调用 `./install.sh /usr/local/bin` 往系统目录写，不能用于 conan 打包）。

手工探索（干净环境一次成功）：

```bash
cd smstools3-3.1.21/src
make CC=clang -j1          # ← 首失败，见问题表 #1
make CC=clang CFLAGS='-fcommon -DNUMBER_OF_MODEMS=64 -DNOSTATS -D_FILE_OFFSET_BITS=64 -W -Wall' -j1
```

配方写法：`generate` 阶段用 `AutotoolsToolchain` 注入 `-fcommon` 与上游必需宏，
`build()` 把 `tc.vars()` 的 CC/CFLAGS/LFLAGS 显式传给 make（R33：不从 shell 环境取编译器）。
产物 bin/smsd 在 OHOS 上按仓库既有做法 objcopy 去 .codesign 后 binary-sign-tool 自签 + chmod 755。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接期 `ld.lld: error: duplicate symbol: d_report / d_report_copy / d_phonecalls / d_saved ...`，`smsd` 不生成 | smsd.c 与 charshift.c 等以 tentative definition 方式定义同名全局变量；clang>=10 默认 `-fno-common`，lld 不再合并 COMMON 符号（与 alex4 / arpalert 同族已知问题） | `tc.extra_cflags.append("-fcommon")`，不改源码、不打补丁。探索时先 `make clean`，否则旧 .o 不重编仍报同错 |
| 2 | 加 `-fcommon` 无效，仍报 duplicate symbol | 上游 `CFLAGS = -D NUMBER_OF_MODEMS=64` 是普通赋值，命令行/环境传入的 CFLAGS 被 Makefile 覆盖或整体替换的语义要分清 | 用 `make CFLAGS="<conan cflags> -fcommon -DNUMBER_OF_MODEMS=64 -DNOSTATS -D_FILE_OFFSET_BITS=64 -W -Wall"` 一次性给全（命令行赋值优先于文件内赋值） |
| 3 | 不带 `NOSTATS` 时链接规则报 `mm-config: Permission denied`/找不到命令 | `src/Makefile` 在非 NOSTATS 分支用反引号调用 `mm-config --cflags/--ldflags`（MagicMirror 统计库，OHOS 不存在） | 保留上游默认 `-DNOSTATS`（发行包默认即关闭统计），不引入新补丁 |
| 4 | 编译出的 smsd 首次执行报 `can't execute: Permission denied` | 签名/复制后文件模式为 0640，OHOS 对可执行文件的模式与签名都有要求 | `package()` 里 chmod 0755 + binary-sign-tool 自签（仓库既有做法），复测可执行 |

## 源码修改

无。全部适配通过编译参数完成，patches/ 为空。

## 依赖版本

无第三方依赖（仅 libc / POSIX）。`NUMBER_OF_MODEMS=64` 为上游默认值，未改动。

## 上游测试清点（R51）

- 顶层 Makefile 目标：compile / install / uninstall / clean / package —— 无 check/test
- src/Makefile 目标：all / smsd / clean —— 无 check/test；`make -n check` → No rule to make target
- src/ 14 个 .c 全为产品代码，无测试框架、无测试注册入口 → **N_static = 0**
- 包内唯一含 test 字样的文件是 `scripts/smstest.php`：需要跑起来的 smsd + 实体 GSM modem
  才能发短信的 PHP 演示脚本，不是可自动执行的用例，不计入上游用例数

因此本 PR 适配后用例全部由 test_package 消费者测试补位（1 个测试程序 / 8 条断言）。

## 验证结果

消费者测试（对探索构建的 bin/smsd 直接执行，全部真跑）：

```
$ sh test_smstools.sh ~/builds/smstools-3.1.21.work/src/smsd ~/tmp/uc2/smstools
PASS help-exit-code
PASS help-summary-line
PASS help-usage-section
PASS encode-hello
PASS decode-hello
PASS roundtrip-hello-world
PASS missing-config-exit-code
PASS missing-config-message
smstools consumer tests: 8 passed, 0 failed
```

断言内容（都不依赖 modem）：
- `-h` 退出码 0 + 摘要行 `smsd spools incoming and outgoing sms.` + Usage 段
- `-EHello` → `C8329BFD06`（GSM 7bit packed 编码，覆盖上游 pdu.c 编码表）
- `-DC8329BFD06` → `Hello`
- `-E"Hello world"` 再 `-D` 解回 → `Hello world`（往返一致）
- 配置文件不存在 → 非 0 退出 + `Cannot open config file` 错误信息

W3/W4/CI/AI 结果见本文件末尾的 finish 收尾块与 PR 评论。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/smsd | 唯一可执行产物（打包自签后 408000 字节，OHOS ELF；探索构建阶段 506304 字节，两口径同源见 W3 日志） |
| licenses/LICENSE | GPL-2.0-or-later（上游 LICENSE 为 HTML 包裹的 GPL 全文） |
| share/smstools/examples/smsd.conf.{easy,full,net,non-root} | 上游 4 个配置样例，便于使用者起服务 |
| archives/s/smstools/commands.json | R38 命令行工具声明 |

## 注意事项

- 守护功能（真正收发短信）需要实体 GSM modem 与 `/etc/smsd.conf`，OHOS PC 上无 modem，
  运行时只验证到不依赖 modem 的确定性行为；此限制已在 PR 正文"已知限制"中如实写明。
- 上游默认使用 inotify 监视 spool 目录（`-D DISABLE_INOTIFY` 可关）。本次不改，
  构建与链接均通过，运行期行为限于无 modem 可验证的范围。
- 路径 B 判断：本次 -fcommon 症状与既有条目（alex4/arpalert 先例、经验汇总已收录的
  "clang>=10 tentative definition → lld duplicate symbol"家族）完全一致，
  未出现该家族已知行为之外的新偏差，故按 **纯路径 A** 交付，不新增知识条目。
---

**编译结束**: 2026-09-20 23:05
**最终状态**: built
