# 上游测试套件在 OHOS 真机跑不起来的三连坑：tmpfile、带参 shebang、自引用硬链接

> Draft: DRAFT-LIBNVME-1162-OHOS-TEST-INFRA-TRIO
> Stem: `libnvme-1.16.2-ohos-test-infra-trio` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-LIBNVME-1162-OHOS-TEST-INFRA-TRIO
- **严重度**: 2
- **类别**: testing|ohos-platform|toybox|musl|portability
- **触发工具**: meson|meson test|bash|toybox tar|clang
- **阶段**: testing
- **来源**: libnvme 1.16.2 适配（任务卡 #15014，feat/libnvme-1.16.2）

## 错误特征

三条互不相关却经常同时出现的"测试起不来"症状：

```
# ① tmpfile 坑（测试二进制直接 exit 1）
test-mi: can't create temporary file for log buf: Permission denied

# ② 带参 shebang 坑（测试包装脚本 exit 127）
env: exec bash -e: No such file or directory
# 且当被调脚本是 find_program() 发现的测试目标时，mtest 抛
# FileNotFoundError 崩掉整个测试运行器（非单个 FAIL）

# ③ 自引用硬链接坑（夹具解包失败）
tar: can't link 'sys/devices/.../uevent' -> 'sys/devices/.../uevent': No such file or directory
```

## 根因分析

三条都是"上游测试逻辑正确、OHOS 运行环境语义差异"：

1. **musl tmpfile() 不遵循 TMPDIR**。glibc 的 tmpfile() 遵循 TMPDIR，
   musl 硬编码 /tmp；OHOS /tmp 是只读 EROFS。实测 `TMPDIR=$HOME/tmp`
   下重跑仍然 EACCES——设环境变量救不了，必须改代码。

2. **toybox env 不支持带参数的 shebang**。`#!/bin/bash -e` 里
   "bash -e" 整体被当作一个程序名去 exec（ENOENT）。即使 PATH 上
   有 bash（/data/service/hnp/bin/bash）也无效——env 根本没走到
   PATH 查找那一步就失败了。附带伤害：meson 的 mtest 对测试目标
   ENOENT 抛未捕获 FileNotFoundError，一个脚本挂掉整轮测试全崩，
   连部分结果都不出。

3. **toybox tar 无法复现自引用硬链接**。sysfs 快照 tarball 里
   138 个成员标记为 "link to 自身"（tar 归档硬链接的标准写法是
   后来者 link to 先出现者，但快照工具对只出现一次的文件也写了
   自引用条目）。toybox tar 的实现是先 unlink 目标再 link，自引用
   时源已被自己删掉 → ENOENT。GNU tar 能吃下这种归档。

## 解决方案

全部是测试辅助文件的最小补丁，断言零改动：

```diff
# ① tmpfile → TMPDIR + mkstemp（test/utils.c）
-fd = tmpfile();
-if (!fd) err(EXIT_FAILURE, "can't create temporary file for log buf");
+tmpdir = getenv("TMPDIR"); if (!tmpdir || !*tmpdir) tmpdir = "/tmp";
+snprintf(path, sizeof(path), "%s/libnvme-test-log-XXXXXX", tmpdir);
+fd_num = mkstemp(path);
+if (fd_num < 0) err(EXIT_FAILURE, "can't create temporary file for log buf");
+if (unlink(path)) printf("warning: can't unlink temporary file %s\n", path);
+fd = fdopen(fd_num, "w+");
```

```diff
# ② 带参 shebang → env + 体内 set -e（test/*/*.sh）
-#!/bin/bash -e
+#!/usr/bin/env bash
 # SPDX-License-Identifier: LGPL-2.1-or-later
+set -e
```

```bash
# ③ 容错提取：tar -xk 保留先落盘的普通文件，自引用硬链接报
#    "File exists" 被忽略；以关键目录存在为成功判定
if ! tar -xk -f "${SYSFS_INPUT}" -C "${TEST_DIR}" 2>/dev/null; then
    [ -d "${TEST_DIR}/sys" ] || exit 1
fi
```

**testlog 解析注意**：meson-logs/testlog.txt 是 `test:` + `result:`
键值对段格式（如 `result: exit status 0`），不是终端输出的
"N/M name OK" 行格式；should_fail 目标在 testlog 里只有裸退出码，
需要按测试名白名单映射为 EXPECTEDFAIL。

## 兜底方案

若不允许打补丁：① 用 LD_PRELOAD shim 拦截 tmpfile()（DejaGNU 先例
E272）；② 把 bash 脚本测试逐个从 meson test 排除；③ 夹具 tarball
重打包为无硬链接版本。代价都大于三个最小补丁。

## 验证构建

- libnvme 1.16.2 conan create（本 PR 配方）：
  上游 meson test 38 注册 → 36 OK + 2 EXPECTEDFAIL + 0 FAIL
  （修复前三坑时分别是 2 FAIL + mtest 崩溃 + 7 FAIL）
- 本机（OHOS aarch64 原生）conan create RC=0 + 干净缓存复验 RC=0
