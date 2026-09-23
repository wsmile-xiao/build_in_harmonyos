# bti

`bti`（bash twitter/identi.ca ididocy）是一个命令行客户端：把标准输入或
bash 管道里的文本直接发布成 twitter / identi.ca 的状态更新，用于把长命令的
输出快速分享出去。

- 上游官网：<https://gregkh.github.io/bti/>
- 源码仓库：<https://github.com/gregkh/bti>
- 许可：GPL-2.0-or-later

## 功能概述

- `bti --action=update`：把 stdin 内容作为状态更新发布
- `bti --action=public|friends|replies|user|direct`：读取时间线/好友/回复/私信
- `--retweet <id>` / `--replyto <id>`：转推与回复
- `--dry-run`：构造完整请求但不真正发出（本仓库用它做离线行为测试）
- `--bash` / `--background`：作为 bash 钩子后台运行
- 附带 `bti-shrink-urls` 脚本（把 URL 交给 2tu.us/bit.ly 等缩短服务）

## OHOS 适配

- 上游发布 tarball 是 `make dist` 产物，自带预生成 `configure`，配方不需要
  `autoreconf`；这一点很重要，因为 CI worker 的 PATH 里没有 automake。
- **HMDFS 目录模式**：`config.status` 用 `umask 077` 创建临时目录，落盘为
  0700 目录；在 setgid hmdfs 挂载上该目录对构建用户不可写，`configure` 报
  `can't create ./confXXXXXX/subs1.awk: Permission denied`。补丁放宽为 022。
- **json-c 版本**：json-c 0.13 起移除 `is_error` 宏，补丁把 3 处调用改为显式
  `!= NULL` 比较（与 Debian `bti_034-6` 同口径）。
- **辅助脚本 shebang**：`bti-shrink-urls` 上游写的是 `#!/bin/bash`，OHOS 没有
  `/bin/bash`（bash 只在 harmonybrew 的 `~/.harmonybrew/bin`），直接执行报
  `bad interpreter`（rc=126）。补丁改为 `#!/bin/sh`，实测 `sh -n` 与 `--help` 通过。
- 运行期 readline 不是构建依赖：上游用 `dlopen` 尝试加载
  `libreadline.so.6/5/4`/`libedit.so.2`，设备上没有时回退到 `fgets`。

## 依赖关系

- 编译依赖（`configure` 的 `PKG_CHECK_MODULES`）：`liboauth`、`libcurl`、
  `libxml-2.0`、`json-c`、`libpcre`（PCRE1，非 PCRE2）。
- 运行依赖：`libcurl.so`、`libxml2.so.16`、`libjson-c.so.5`（三者由 Conan
  依赖链提供）；`liboauth`/`pcre`/`openssl` 为静态链接。
- 依赖图注意：已发布的 `liboauth/1.0.3` 钉 `openssl/1.1.1w`、已发布的
  `curl/8.15.0` 钉 `openssl/3.5.6.1`，二者硬冲突；`bti` 配方用
  `self.requires("openssl/3.5.6.1", override=True)` 统一，代价是 `liboauth`
  在构建下游时从源码重建。

## 参考资料

- 上游 README 与 man page（`bti.1`）
- Debian 打包补丁 `replace_removed_is_error.patch`（`bti_034-6`）
