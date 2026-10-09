# ruptime 1.8 适配笔记

## 上游信息

- 上游仓库：https://github.com/alexmyczko/ruptime（poor man's ruptime，Shell）
- 上游版本：1.8（tag `1.8`，commit `42fb963b1d05256e55b28cd101993bfd91c97407`）
- 许可证：AGPL-3.0（源码包 LICENSE.md 为 GNU Affero General Public License v3）
- 源码包：`https://github.com/alexmyczko/ruptime/archive/refs/tags/1.8.tar.gz`
  （22 300 字节，sha256 见 conandata.yml，已实测下载验证）

## 源码审计（上游无测试的依据）

tag 1.8 解包共 21 个条目，无构建系统、无测试框架、无 CI 测试配置：

```text
LICENSE.md README.md
etc/cron.d/ruptime etc/ruptime/ruptime.conf etc/ruptime/ruptime.key
man/ruptime.1 man/ruptimed.8
ruptime ruptimed                       # 两个 bash 脚本，无其他源码
systemd/ruptimed.service sysv/ruptime web/README web/ruptime.cgi
```

- `find . -iname '*test*'` 无命中；无 Makefile/configure/CMakeLists.txt/meson.build。
- 结论：上游 1.8 不提供任何测试套件（test_package/MANIFEST.yml 记
  `upstream_tests_exist: false` 并附本审计）。

## 适配内容

纯 shell 包，无编译步骤。conanfile.py 只做三件事：

1. 拷贝 `ruptime`（客户端）、`ruptimed`（采集 daemon）到 `bin/`（755），
   man 页到 `share/man/man{1,8}`，README 到 `share/doc/ruptime`，
   LICENSE 到 `licenses/`。
2. OHOS 适配：上游 shebang `#!/bin/bash` 在 HarmonyOS 上不存在
   （仓库内 mtools/privoxy/cht.sh/adr-tools 均有同类处理），改写为
   `#!/usr/bin/env bash`；运行时 bash 由 `requires("bash/5.3")` 提供，
   并经 buildenv/runenv PATH 前置保证可用。
3. OHOS 适配：上游硬编码 `/etc/ruptime/ruptime.conf(.key)`，而 HarmonyOS PC
   真机 `/etc` 只读（`mkdir /etc/ruptime` 报 Read-only file system）。
   配方在 `build()` 内把 `/etc/ruptime` 改写为
   `${RUPTIME_CONF_DIR:-/etc/ruptime}`：不设置变量时行为与上游一致，
   设置时指向临存目录；无平台宏，可移植。
4. `build()` 内用依赖 bash 对两个脚本做 `bash -n` 语法检查
   （上游无 `make check` 可调）。

未使用 `patches/`（改写在配方代码内完成，无源码语义改动）。

## 依赖版本

- `bash/5.3`（requires；仓库 `archives/b/bash/5.3` 已有归档，
  制品仓发布状态待真机 `conan create` 实测确认）

运行时（非 Conan requires，沿用 cht.sh 的做法仅文档声明，需目标机具备）：

- 客户端查询路径：`nc`、`xz`、`openssl`；指标采集：`uptime`、`free` 等；
  daemon 侧：`mini-inetd`/`tcputils`（`getpeername`）、`nc`、`xz`、`openssl`。

## 已知限制

- 上游 `-v` 输出的版本串未随 tag 更新（1.8 源码仍打印 `version 1.6`），
  属上游问题，测试仅断言输出含 `version`，不断言具体版本号。
- 冒烟测试全程 hermetic：经 `RUPTIME_CONF_DIR=$TMPDIR/...` 暂存配置与 key，
  从不写 `/etc`（真机只读）；退出时自动清理。断言仍为 6 项，语义不变。

## 验证结果

- 本轮：工作树已完成，未提交；待 HMBS 真机 `conan create` 全量验证
  （含 test_package 6 项断言与 rule4 门禁）。
- manifest.yaml 状态 `built` 为配方完成标记，真机通过后由 HMBS 更新。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/ruptime` | 客户端脚本（shebang 已适配） |
| `bin/ruptimed` | 采集 daemon 脚本（shebang 已适配） |
| `share/man/man1/ruptime.1` | 客户端 man 页 |
| `share/man/man8/ruptimed.8` | daemon man 页 |
| `share/doc/ruptime/README.md` | 上游 README |
| `licenses/LICENSE.md` | AGPL-3.0 许可证文本 |
