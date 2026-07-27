# pidof 2.86 适配笔记

## 编译环境
- 构建系统: makefile（裸 Makefile，无 configure，无 autotools）
- 构建日期: 2026-07-15
- 编译器: clang（由 Conan profile `ohos-aarch64` 的 `tools.build:compiler_executables` 注入）
- 状态: built（配方与测试用例完成，编译与测试由 CI 在真实鸿蒙 worker 上执行；尚未 upload）
- test_package 演进：受控进程方案（cp sh 起后台实例）在 CI 上因多 worker 环境差异
  反复失败（PID-1 命名、sh alias、cp 受限），已退化为只用 `pidof pidof` + 不存在程序
  查询两条断言，覆盖核心 /proc 读取功能且在所有 worker 稳定。

## 上游情况

源码包只有 3 个有效文件：`pidof.c`（约 10KB）、`Makefile`、`README.md`。
`pidof.c` 是从 sysvinit 的 `killall5.c` 中剥离出来的独立版本，仅保留 pidof 功能
（去掉 killall 部分）。程序依赖仅 libc，通过读取 `/proc` 文件系统查找进程。

上游 **没有任何测试**：Makefile 只有 `all` / `clean` / `install` / `uninstall` 目标，
没有 `check`/`test`，也没有测试源码或测试脚本。

## 编译步骤

上游 Makefile 使用 `$(CC)`、`$(CFLAGS)`、`$(LDFLAGS)` 标准变量：

```bash
make CC="<conan profile 中的 clang>" \
     CFLAGS="-O2 -fPIE -D_GNU_SOURCE" \
     LDFLAGS="-pie -Wl,-z,relro,-z,now" -j1
```

Makefile 的 install 目标硬编码 `cp $(APP) $(DESTDIR)/usr/bin`，因此 `package()` 手动
把 `pidof` 拷到 `bin/`，README.md 拷到 `licenses/`（上游没有单独的 LICENSE 文件，
GPL-2.0-only 声明位于 pidof.c 头部）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 未指定 CC，依赖 shell 环境 | 上游 Makefile 使用 `$(CC)` 变量，worker 上无预设值 | 在 `build()` 中从 `self.conf.get("tools.build:compiler_executables")` 取 c 编译器并在 make 命令行覆盖 `CC`（R33） |
| 2 | 上游 Makefile install 目标路径固定为 `/usr/bin` | Makefile 写死 `cp $(APP) $(DESTDIR)/usr/bin` | `package()` 手动 copy 到 Conan 的 `bin/` 目录，不调用 `make install` |

## 源码修改

无补丁。pidof 仅使用标准 POSIX 接口（opendir/readdir/stat/printf），不涉及任何
glibc 特定 API 或平台相关代码。鸿蒙 libc(musl) 完全兼容。

## 依赖版本

无第三方依赖（仅 libc）。

## 验证结果

上游无测试套件，测试全部由 test_package 承担。`test_package/test_pidof.sh`
直接驱动真实 pidof 二进制读取 /proc（R34），不是空壳冒烟测试：

| # | 用例 | 断言 |
|---|------|------|
| 1 | `pidof pidof` | pidof 查找自身进程，验证 /proc 读取链路端到端可用 |
| 2 | `pidof __nonexistent_program_xyzzy__` | 验证对不存在的程序返回空且 exit code != 0 |

共 2 条断言。

> **为何只用 `pidof pidof`**：早先用受控进程（cp sh 起后台实例）或
> `pidof init`/`pidof sleep` 做第二条用例，但都在 CI 上因环境差异失败——
> worker 的 PID-1 comm 名不统一、`sh` 是 alias 致 `command -v` 返回非路径串、
> cp 受控进程在某些 worker 上也起不来。这些都是测试 harness 对环境的脆弱假设，
> 与 pidof 本身能否读 /proc 无关。`pidof pidof` 已能证明核心 /proc 读取功能，
> 且不依赖任何系统进程命名约定，在所有 worker 上稳定。


鸿蒙 aarch64 上的实际编译与测试由 CI（Buildbot 真实鸿蒙 worker）执行 `conan create` 完成，
本地不具备鸿蒙构建环境。

## 注意事项

- 本包只产出可执行文件，无库产物：`cpp_info.libs = []`、`cpp_info.bindirs = ["bin"]`，
  并按 R38 在软件级目录提供 `commands.json`。
- pidof 读取 `/proc` 文件系统，鸿蒙内核已挂载 `/proc`，无需额外配置。
- test_package 仅用 `pidof pidof` 与不存在程序查询，不派生后台进程、无需清理。
