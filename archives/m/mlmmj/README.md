# mlmmj

mlmmj（Mailing List Minder / "Mailing List Made Just right"）是一个轻量的邮件列表管理器（MLM）套件：由一系列小工具驱动一个纯文件系统的列表目录，不依赖专用守护进程或数据库。

## 功能概述

- **订阅管理**：`mlmmj-sub` / `mlmmj-unsub` 支持正常/摘要（digest）/禁邮（nomail）三种订阅形态
- **列表查询**：`mlmmj-list` 输出成员、计数（`-c`）、摘要者（`-d`）、禁邮者（`-n`）、版主（`-m`）、所有者（`-o`）
- **收信与分发**：`mlmmj-receive`（MTA 管道入口，别名 `mlmmj-recieve`）、`mlmmj-process`、`mlmmj-send`
- **退信处理**：`mlmmj-bounce` 解析 DSN 并按策略暂停/退订地址
- **维护**：`mlmmj-maintd` 单遍维护（归档、清理、探针）
- **建列表**：`mlmmj-make-ml`（shell 脚本，支持 `-f answerfile` 全非交互；别名 `mlmmj-make-ml.sh`）

包内布局：`bin/` 11 个命令；`share/mlmmj/text.skel/en/` 17 个列表文本骨架；`share/man/man1/` 9 个手册页。

## OHOS 适配

1. **三元组识别**（0001/0002）：2018 年版 `build-aux/config.guess` / `config.sub` 不认识 HarmonyOS。补丁使 `config.guess` 在 `__OHOS__` 上输出 `aarch64-unknown-linux-ohos`，并教 `config.sub` 接受 `ohos` / `linux-ohos` 系统名（maybe_os 列表、`ohos-linux` 分支、主白名单三处）。原生 configure 自检通过，不使用 `--build=/--host=`。
2. **HMDFS 临时目录**（0003）：configure 用 `umask 077` 创建 `confXXXXXX`，HMDFS 的 UID 映射使该目录对当前进程不可写（知识库 E011）→ 改为 `umask 022`。
3. **符号链接**（0004）：安装钩子用 `ln -f -s` 创建 `mlmmj-recieve` / `mlmmj-make-ml.sh` 别名；HMDFS 全盘禁 symlink（EPERM，知识库 E050）→ 改为 `cp -f`。
4. **可重定位**（0005）：`mlmmj-make-ml` 的 `@textlibdir@` 被 configure 替换为构建期绝对路径，Conan 包搬移后失效 → 脚本改为优先解析自身所在目录的 `../share/mlmmj/text.skel`，找不到时回退到编译期默认值。
5. **memstream 收尾**（0006/0008）：`strgen.c` 的 `decode_qp()` 与 `include/xstring.h` 的 `xstring_free()`/`xstring_get()` 在 `fclose()` 前补 `fflush()`——OHOS libc 的 `fclose()` 丢弃未 flush 的 `open_memstream` 缓冲（0008 还使流在退出期崩溃）。
6. **列表属主检查**（0007）：`mlmmj.c` 的 `open_listdir()` 在 uid 与 st_uid 不一致时回退为 `access()` 可写性判定（HMDFS stat() 一律报存储属主、进程为每会话 uid，单凭 uid 比较会拒绝合法属主）；属主与 root 保持原直过行为、不可写者仍拒绝，纯 POSIX 无平台条件编译。
7. **测试环境**：上游 `make check` 依赖 kyua；设备上无 kyua，ATF 测试脚本用 `atf-sh` 直跑。测试脚本中准备 listtexts 的 `ln -s` 在 HMDFS 上同样失败（E050），设备测试运行用 PATH 垫片（`ln -s` → `cp -Rf`）与 atf-c 程序的 LD_PRELOAD `symlink()` 拦截器，上游测试文件零修改。

## 依赖关系

- 运行时：无外部依赖（仅 OHOS libc；列表操作均为纯文件系统操作）
- 构建：clang（OHOS SDK）；`--disable-tests` 时不需要 ATF
- 上游测试（可选）：ATF 0.23（设备上有对应适配包）

## 参考资料

- 官网：http://mlmmj.org/
- 源码：https://codeberg.org/mlmmj/mlmmj/releases/download/RELEASE_1.6.0/mlmmj-1.6.0.tar.gz（上游发布已迁至 Codeberg；mlmmj.org 旧 releases/ 路径已失效）
- 知识库条目：E011（HMDFS umask）、E050（HMDFS symlink EPERM）、E490（autotools 脚本执行位）
