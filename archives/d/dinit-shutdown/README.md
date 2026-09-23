# dinit-shutdown

dinit 服务管理器的系统关机工具集。它以发行版拆分包的形式提供 dinit 上游（davmac314/dinit）
中负责「停止服务并关闭系统」的那部分命令，服务管理器本体 `dinit` 不在本包内。

- 上游项目: <https://github.com/davmac314/dinit>
- 项目主页: <https://davmac.org/projects/dinit/>
- 许可证: Apache-2.0

## 功能概述

包内提供 5 个可执行文件，它们内容相同，程序按 `basename(argv[0])` 决定默认动作
（见上游 shutdown(8)）：

| 命令 | 默认动作 | 说明 |
|------|----------|------|
| `dinit-shutdown` | power down | 通用入口，可用选项改动作 |
| `dinit-poweroff` / `dinit-halt` | power down | 与其它软件包的命名习惯保持一致的别名；上游明确说明二者**无特殊语义** |
| `dinit-reboot` | reboot | 等价于 `dinit-shutdown -r` |
| `dinit-soft-reboot` | soft reboot | 等价于 `dinit-shutdown -s`，重启 dinit 与全部用户态服务而不重启内核 |

通用选项：

```text
-r               重启
-h               停机（不关机）
-p               关机（默认动作）
-s               软重启（以相同启动参数重新启动 dinit）
-k               kexec 到已加载的新内核
--use-passed-cfd 使用环境变量 DINIT_CS_FD 指定的、由父进程传入的 socket 连接
--system         不经过服务管理器直接关机（仅在管理器无响应时使用）
```

工作方式：默认情况下工具连接服务管理器的控制 socket，发送 shutdown 命令，由 dinit 回滚
服务、执行关机钩子并最终关机；`--system` 才由工具自己执行关机。

## OHOS 适配

针对 HarmonyOS PC (aarch64, `os=OHOS`) 的适配要点：

1. **显式打开 shutdown 工具**：上游 `configure` 仅在 `uname` 报告 `Linux` 时默认
   `BUILD_SHUTDOWN=yes`，而 HarmonyOS PC 的 `uname -s` 是 `HarmonyOS`，需要
   `--enable-shutdown`；同时用 `--shutdown-prefix=dinit-` 让安装名与编译期
   `SHUTDOWN_PREFIX`（argv[0] 分派表）一致。
2. **大小写不敏感文件系统**：上游 release tarball 顶层同时含 `BUILD` 文档与 `build/` 目录，
   而设备工作区（HMDFS）大小写不敏感，Python tarfile 创建 `build/` 会抛 `FileExistsError`，
   `conan get()` 在构建前失败。`source()` 用 `get(..., excludes=["dinit-0.21.0/BUILD"])`
   排除该文档文件（无构建规则读取它），其余内容逐字节原样解包。
3. **不剥离调试信息**：OHOS 工具链产物带 `.codesign` 段，`strip` 后二进制在本平台无法加载
   （退出码 126），因此 `--disable-strip`，且不对 `.so`/可执行文件重新签名。
4. **控制 socket 路径**：编译期固定为 `/var/run/dinitctl`（上游对非 Linux 平台的默认值，
   与已归档的 dinit 0.22.0 OHOS 适配一致）。运行前需保证该路径存在且 dinit 监听同一地址；
   也可由 dinit 通过 `DINIT_CS_FD` + `--use-passed-cfd` 复用已建立的连接。

## 依赖关系

- 编译依赖: 无（仅 libc/libc++；上游自带 configure + make）
- 运行依赖: 需要一个正在运行的 dinit 服务管理器实例（另一软件包/系统组件），
  二者必须配置相同的控制 socket 路径

## 验证

- 上游单元测试：`make -C src check`，136/136 通过（设备原生，见 `0.21.0/notes.md`）
- 消费者测试：`test_package/` 对 5 个已安装可执行文件逐个实跑 `--help`、未知选项与
  无守护进程时的 connect 失败路径（39 条断言），外加 **9 条鸿蒙平台契约断言**（共 48 条）：
  产物为 64 位 LE AArch64 PIE、保留 `.codesign` 段、保留 `.symtab`（未 strip —— 本平台
  strip 后加载失败 rc=126）、编译期控制 socket 为 `/var/run/dinitctl`、编译期前缀字面量
  `dinit-reboot`/`dinit-soft-reboot` 以 NUL 结尾字面量精确存在、4 个别名与主体字节一致；测试不会发送任何关机命令

## 参考资料

- 上游仓库: <https://github.com/davmac314/dinit>
- 上游手册 shutdown(8): `doc/manpages/shutdown.8.m4`
- 发行版拆分先例: Alpine `dinit-shutdown` 子包（同一上游 tarball + `--shutdown-prefix=dinit-`）
