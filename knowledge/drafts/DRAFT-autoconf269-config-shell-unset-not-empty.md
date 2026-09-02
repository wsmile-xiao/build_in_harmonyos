# DRAFT-autoconf269-config-shell-unset-not-empty — autoconf 2.69 CONFIG_SHELL 重执行块 + 绕过必须 unset 而非置空

> **Contributor**: Awstme | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: blocking (2) | **Category**: autotools / conan / ohos / hmdfs / shell
> **Audience**: 所有在 OHOS/Conan 环境下构建 autoconf 2.69 时代 configure、且 profile 设置 CONFIG_SHELL 的配方维护者

## 触发（trigger）

- CI/Conan profile 设置 `CONFIG_SHELL`（指向 hnp bash 5.3）。
- 目标软件由 **autoconf 2.69** 生成 configure（libaudclient 3.5-rc2 发布 tarball 自带）。
- HMDFS 工作区，继承的 PWD 可能过期（Conan 切目录后）。

## 症状（symptom）

两层失败，分别出现：

1. configure 阶段（CONFIG_SHELL=bash 时）：
   `configure: error: working directory cannot be determined`，伴随
   `shell-init: error retrieving current directory: getcwd: ...` errno 风暴。
2. make 阶段（用 CONFIG_SHELL= 置空绕过 (1) 后）：
   `make: -c: No such file or directory`（Error 127，buildsys.mk:111 all）；
   `make -p | grep '^SHELL'` 输出 `SHELL = `（空）。

## 机制（root cause）

1. **重执行块是 autoconf 版本行为**：autoconf 2.69 生成的 configure 在启动段
   （139-154 行附近）当 CONFIG_SHELL 非空时无条件 `exec $CONFIG_SHELL`
   重执行自身；**2.71 生成的 configure 无此块**（dbus-glib 0.114 同设备同
   profile 未触发——版本差异是排查时容易忽略的变量）。hnp bash 5.3 启动时
   getcwd() 在 HMDFS 上对过期 PWD 失败（toybox /bin/sh 不受影响），configure
   的 ac_pwd 检查随即中止。
2. **置空 ≠ 未设置**：configure 前导 `SHELL=${CONFIG_SHELL-/bin/sh}` 只在
   CONFIG_SHELL **未设置**时回退 /bin/sh，"空但已设置"不回退。空 SHELL 被
   AC_SUBST 固化进 buildsys.mk/Makefile；GNU make 用空 SHELL 拼接
   `[-c, recipe]` 后直接 exec `"-c"` → Error 127。失败点在 configure 之后，
   与 configure 的成功形成误导性反差。

## 修复（rec）

配方 build() 内、调用 configure 前显式 **unset**（不是赋空）：

```python
self.run(f'unset CONFIG_SHELL; '
         f'"{os.path.join(self.source_folder, "configure")}" '
         f'{toolchain_args.get("configure_args")}',
         cwd=self.build_folder, env="conanbuild")
```

unset 后：重执行块不触发；`${CONFIG_SHELL-/bin/sh}` 真正回退 /bin/sh
（toybox ash，无 getcwd 问题）；AC_SUBST 进 buildsys.mk 的 SHELL=/bin/sh。
另一条等效轨道（姊妹草稿）：保留 CONFIG_SHELL=bash 并预置
`os.environ["PWD"] = str(self.build_folder)`。两轨择一。

## 查重（dedup）

- 姊妹草稿 DRAFT-ohos-autotools-configure-re-exec-cwd-env（GoliWie，2026-08-25）：
  同一 getcwd 症状链，修复为预置 PWD。本条目增量：(a) **autoconf 2.69/2.71
  重执行块版本差异**（姊妹草稿未区分）；(b) **unset-not-empty 陷阱与空 SHELL
  经 AC_SUBST 泄漏进构建文件 → make: -c** 这条全新下游失败链（含
  `make -p | grep '^SHELL'` 诊断法）；(c) 与预置 PWD 互为替代轨道的关系。
- E232：Conan `Autotools.configure()` 首进程 exec 被拒（Permission denied/126），
  发生在 autoconf 启动之前，错误签名与修复面不同；其 scope boundary 明确
  不含后续 autoconf 临时目录/重执行问题。
- E011/E129/E206/E223/E110/E112 系（umask 077/config.status 临时目录）：不同失败。
- 全库 grep `make: -c`/`AC_SUBST.*SHELL`/`2.69`：无命中。

## 证据（evidence）

- 设备实跑链（HarmonyOS PC aarch64）：run5 "working directory cannot be
  determined" → 置空绕过 → run6 `make: -c: No such file or directory`
  （`make -p` 实锤空 SHELL）→ run7 `unset CONFIG_SHELL` 后 configure+make 全通。
- 配方提交：1e68583d99（unset + 注释记录机制）；
  PR https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/7671。
- 禁止做法实证：CONFIG_SHELL= 路线已在 run6 真实翻车，非理论推演。

## 关系

- similar_to: E232、E010、E011、DRAFT-ohos-autotools-configure-re-exec-cwd-env
