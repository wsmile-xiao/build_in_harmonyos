# ccd2cue 0.5 适配笔记

## W0/W0b 与源码确认

- 任务 #7245，分支 `feat/ccd2cue-0.5`，源码来自官方 GNU FTP。
- W0：初始归档无依赖；源码确认使用 GNU argp，OHOS/musl 缺少 `argp.h`，精确核验 `argp-standalone/1.5.0` 的 OHOS armv8 binary 已在 `ohpcd` 制品仓可下载；带 OHOS sysroot 的头文件探针确认 `err.h`/`sysexits.h` 已存在。
- W0b：上游无历史归档；`init-build` 后确认 build system=Autotools，11 个 C 源文件，task=c 与源码主体一致。
- 官方 tarball SHA256：`8725cfdbcb963259ff094a878aa0e49ea8284e1071ea36ac7ea47358c49b99c5`。

## 适配变更

- `build-aux/config.guess`：增加 HarmonyOS/aarch64 triplet、直接返回识别结果，并把 HMDFS 临时目录探测从 `umask 077` 调整为 `022`。
- `build-aux/config.sub`：接受 `linux-ohos`。
- `src/error.h`：提供 GNU `error(status, errnum, format, ...)` 的最小语义兼容实现，保留 stderr、errno 和非零退出行为。
- `src/errors.c` 保留上游 `err.h`/`sysexits.h` include；OHOS sysroot 已提供这两个头。
- `src/i18n.h`：NLS 关闭时使用字面量消息与 bind/textdomain no-op；启用 NLS 的路径保持原 gettext 逻辑。
- 配方构建时用 `replace_in_file` 修复生成 `configure` 的 HMDFS `umask 077`，不提交生成文件 patch。
- `--disable-nls --disable-doxygen-doc --disable-doxygen-dot` 避免 libintl、makeinfo、doxygen 成为发布构建前置条件。

## 探索证据

1. 原始 configure：目标三元组已可识别，但 `config.status` 因 `umask 077` 报 `can't create ./conf*/subs1.awk: Permission denied`；完整日志保存在任务临时目录。
2. 修复 `umask 022` 后 configure 成功生成全部 Makefile/config.h。
3. 首次 make 报 `fatal error: 'error.h' file not found`；补齐本地兼容头后继续发现 `--disable-nls` 下 gettext 无原型，补 i18n no-NLS 分支；独立 sysroot 探针确认 `err.h`/`sysexits.h` 不需要重复兼容头。
4. 修复后设备 `make -j1`、`make -j1 check`、隔离 `make install DESTDIR=...` 均通过；上游 `make check` 没有注册测试目标。
5. 安装后的真实转换测试：最小 CCD 输入生成 `FILE "sample.bin" BINARY`、`TRACK 1 AUDIO`、`INDEX 01 00:02:00`。

## 测试账本

| 层级 | N_static | N_registered | N_executed | PASS | FAIL | SKIP | 证据 |
|---|---:|---:|---:|---:|---:|---:|---|
| 上游 Autotools TESTS | 0 | 0 | 0 | 0 | 0 | 0 | 源码无 tests/，Makefile 无 TESTS，`make check` 返回 0 |
| 消费者 test_package 程序 | 1 | 1 | 1 | 1 | 0 | 0 | 执行安装包 `ccd2cue`，8 项行为断言 |

## 发现与知识

- ✅ 已查重 E007/E011/E072/E169/E545/E142、相关草稿及 Issue #2874；`error.h` 缺失由 E545 覆盖，argp/NLS 相关知识已有对应条目/Issue，本任务没有独立的新跨仓库知识条目。
- ✅ 本任务按路径 A 交付；`err.h`/`sysexits.h` 的 OHOS sysroot 探针结果作为本版本笔记，不创建重复知识草稿或知识 Issue。

## 对话记录

### 对话 #1

- `pre-analysis` 曾误找归档内源码路径；真实源码由 `init-build` 明确为 `/storage/Users/currentUser/builds/ccd2cue-0.5.work`，该工具限制不影响后续真实验证。
- 目标设备多人共用；高 loadavg 期间未启动并发构建，最终所有构建均单线程执行。

---

编译结束: 2026-09-11
最终状态: built
