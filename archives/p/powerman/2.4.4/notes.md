# powerman 2.4.4 适配笔记

## 编译环境
- 构建系统: autotools（tarball 无 configure，autoreconf -fi 自举）
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4（OHOS SDK llvm，/data/service/hnp/bin/clang）
- 状态: built（conan-verify G0-G4 全过、L2/L4/L5 无 cache 路径合理跳过；PR 未合并、未执行 conan upload，按 R29 标记 built）

## 编译步骤

本机探索编译（工作树 /storage/Users/currentUser/tmp/builds/powerman-2.4.4.work）：

```bash
# 1. 自举（上游 autogen.sh 同款：LT_INIT 需 libtoolize 先行）
libtoolize --automake --copy && autoreconf -fi
# 2. configure：可选守护进程禁用 + CONFIG_SHELL 绝对路径（libtool wrapper shebang）
CONFIG_SHELL=/data/service/hnp/bin/bash bash ./configure \
    --prefix=<prefix> \
    --without-httppower --without-redfishpower --without-snmppower
# 3. 构建 + 安装
make -j8            # conan 内须 -j1（E074），本机探索 -j8 可用
make install DESTDIR=<staging>
```

conan 配方固化（conanfile.py build()）：apply patches → libtoolize --automake --copy →
autoreconf -fi → 生成后修正（configure umask 077→022×2；config/config.guess+config.sub
E007 HarmonyOS 三件套，注意 AC_CONFIG_AUX_DIR([config]) 子目录）→ configure（CONFIG_SHELL
绝对路径 + 三禁用开关 + 剥除 -DNDEBUG）→ make -j1 → autotools.install()。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoconf 硬错误 "AC_INIT: not enough arguments" | AC_INIT 用 m4_esyscmd(git describe)，release tarball 无 .git 版本为空 | patch 0001：固定 AC_INIT([powerman], [2.4.4])（与 tag 一致） |
| 2 | telnet.h compound literal 宏 -Werror=missing-braces；vpcd.c -Werror=string-plus-int 等 | OHOS clang 15 对 musl/glibc 头与字符算术的警告与上游 gcc 构建不同 | patch 0001：clang 分支 WARNING_CFLAGS 追加 5 项 -Wno-error= |
| 3 | xpoll.c: sys/poll.h #warning；xpoll.h: struct timeval 未定义 | musl 严格最小 include 策略（glibc 靠间接 include 掩盖） | patch 0003/0004：<poll.h> 替换 + 显式 <sys/time.h> |
| 4 | t0030-heartbeat-stonith 11/12 FAIL（rc=126） | heartbeat/powerman 与 t/scripts/pm-sim.sh 均 `#!/bin/bash`；OHOS 无 /bin/bash 且 kernel 不查 PATH → bad interpreter | patch 0002/0005：`#!/usr/bin/env bash`；修复后 12/12 PASS |
| 5 | t0003-api-client 7/10 FAIL（bad interpreter） | CONFIG_SHELL=bash 裸名 → libtool check-program wrapper 写 `#! bash` shebang → 同上 kernel 问题 | conanfile：configure 前设 CONFIG_SHELL=绝对路径 bash；本机验证修复后 10/10 PASS |
| 6 | tap-driver.sh "bad file descriptor"（make check 一开始就崩） | OHOS hnp bash 复合命令 `{...} 3>file` 的 fd3 继承异常（Linux bash/mksh 正常） | make check 传 SHELL=/bin/sh（mksh 驱动 tap-driver） |
| 7 | t0029/t0034/t0037-39 redfish 系 FAIL/超时 | redfishpower 守护进程按设计禁用（--without-redfishpower，免 curl+jansson）；查询断言必挂、设备超时重试致单测试 20-55 分钟 | 预期行为，归因记录；t0037-39 未跑（SKIP_TESTS 跳过，同归因）；t0027-redfish-httppower 不依赖被禁二进制全 PASS |
| 8 | conan G2: liblsd/cbuf.c -Wunused-but-set-variable ×4（本机无此错） | conan Release 工具链给 CPPFLAGS 注入 -DNDEBUG（conanautotoolstoolchain.sh 独立 export 行）；assert 是 'l'/'n' 等局部变量唯一消费者，NDEBUG 编译掉 assert → 变量未使用 | conanfile generate()：剥除该行（上游从不 NDEBUG 构建，语义保真）；防御性保留 -Wno-error=unused-but-set-variable 豁免 |
| 9 | conan G2 第二轮: device_tcp.c -Wunused-variable 'tcp' | 同 #8（TcpDev *tcp 只被 assert 消费） | 同 #8 剥 NDEBUG 后消失 |
| 10 | conan 的 config.guess 不识别 HarmonyOS | automake/1.18 工具包是原版 GNU config.guess/sub | E007 三件套注入（__OHOS__ LIBC 探测 + *:HarmonyOS:* 分支 + config.sub ohos-linux/ohos*），带 marker 校验防静默失败；路径在 config/ 子目录（与 posh 根目录不同） |
| 11 | configure/config.status 写临时目录失败 | E011/E114：umask 077 临时目录在 HMDFS UID 映射 setgid 下不可写 | 生成后文本改写 umask 077→022（configure ×2）/ →000（config.guess），带出现次数校验 |

## 源码修改（patches/，全部可对官方 v2.4.4 tarball 干净应用）

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | configure.ac | AC_INIT 固定版本 2.4.4；clang 分支 5 项 -Wno-error= 豁免 |
| 0002 | heartbeat/powerman | shebang → #!/usr/bin/env bash |
| 0003 | src/libcommon/xpoll.c | <sys/poll.h> → <poll.h> |
| 0004 | src/libcommon/xpoll.h | 补 <sys/time.h> |
| 0005 | t/scripts/pm-sim.sh | shebang → #!/usr/bin/env bash |

生成文件类修正（configure umask、config.guess/sub E007、-DNDEBUG 剥离）不进 patches/，
在 conanfile.py build()/generate() 内以生成后文本改写固化（posh/abiword-plugin 先例）。

## 依赖版本

- automake/1.18（tool_requires，CI 无系统 automake）
- libtool/2.5.4（tool_requires，LT_INIT + libtoolize）
- flex/2.6.4（tool_requires，parse_lex.l）
- bison/3.8.2（tool_requires，parse_tab.y）
- 运行时依赖：无（核心 powermand/powerman/plmpower/libpowerman 零外部库）

## 验证结果

conan-verify G0-G4 全过（L2/L4/L5 无 cache 路径合理跳过）；test_package R34 冒烟 16/16 PASS。

上游测试（本机探索树 make check，SHELL=/bin/sh，如实记录）：
- libcommon 单测：test_argv + test_xregex = 58/58 PASS
- t/ sharness 39 个 .t，共 649 断言：**PASS 593 / FAIL 47 / SKIP 9 / ERROR 1**
  - FAIL 47 = t0029-redfish 13 + t0034-redfishpower 34，全部归因 redfishpower
    守护进程按设计禁用（--without-redfishpower，免 curl+jansson）；t0029 的
    ERROR=1 即该 13 FAIL 的退出码，非额外问题
  - SKIP 9 = t0000×5（sharness 框架自测的 skip 机制验证与缺 PERL/COLOR/
    INTERACTIVE 前置的正常跳过）+ t0033×1（OHOS 无 valgrind）+ t0037/38/39
    ×3（SKIP_TESTS 显式跳过，redfish 系同归因）
  - t0030/t0003 为平台缺陷修复后达到全 PASS（见问题表 #4/#5）
  - t0027-redfish-httppower：不依赖被禁二进制，10/10 全 PASS
- 逐项归因详见 test_package/MANIFEST.yml

```bash
# test_package 冒烟（消费者视角，真实起停 daemon）
bash test.sh
# === powerman test.sh summary: PASS=16 FAIL=0 ===

# conan-verify
# ✅ 配方验证通过: powerman 2.4.4（上传后可提升为已发布状态）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | posh 模式配方（tool_requires 四件套 + E007/E011 生成后修正 + NDEBUG 剥离） |
| conandata.yml | 官方单源 URL（镜像由 CI 自动注入，sha256 已验证） |
| patches/0001-0005 | 5 个源码补丁（见上表） |
| test_package/ | R34 冒烟（test.sh 16 断言 + vpc.dev + vpc-sim.sh bash 版模拟器） |
| manifest.yaml / notes.md | 版本级元数据 + 适配笔记 |
| reports/ | conan-verify 报告 |

## 注意事项

- powermand 无 -f 选项、默认前台运行（sharness 用 `powermand -c conf &` 后台化）
- 设备脚本 %s 替换传 hostlist 压缩串（如 `[0-3]`，vpcd 用 hostlist 库解析）——自写
  模拟器须展开方括号区间
- make check 的 tap-driver 必须用 /bin/sh 跑（hnp bash fd3 bug）
- test_package 端口选 47913（避开 powerman 默认 10101 与上游 sharness 11xxx 段）
---

**编译结束**: 2026-09-04 16:32
**最终状态**: built
