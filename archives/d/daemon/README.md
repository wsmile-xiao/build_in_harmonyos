# daemon

将其他进程转换为 Unix 守守进程的命令行工具（raf's daemon，源自 https://libslack.org/daemon ）。
负责处理 setsid、pidfile、respawn、信号、pty、syslog 重定向等守护进程化细节，便于用 shell/Java
等非 C 语言编写守护进程。内置 libslack 静态库。

## 可用版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 0.8.4 | built | makefile |

## 注意事项

- 构建系统为 raf 的自定义 Makefile + `./configure` 平台探测（非 autotools/cmake）
- `--platform=Linux` 强制走 Linux 配置分支（OHOS 内核上报为 Linux）
- CC/AR/RANLIB/LDFLAGS 须在 `make` 命令行传入以覆盖 Makefile 的 `:=` 赋值（R33）
- 链接可执行文件使用 GNU ld（`-fuse-ld=/data/service/hnp/bin/ld`），规避 OHOS SDK lld 对 libxml2.so.16 的依赖
- HarmonyOS 平台要求二进制 ELF 签名后方可执行（package 阶段 `binary-sign-tool`）
- 产物仅为 `daemon` 可执行文件；内置 libslack 为静态库，不对外暴露
