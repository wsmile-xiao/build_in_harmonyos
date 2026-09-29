# json-glib 1.10.8 适配笔记

## 当前状态

- 日期：2026-09-26
- 构建系统：Meson
- 目标：HarmonyOS PC arm64
- 状态：本机 OHOS 交叉构建与消费者编译/链接通过；USB HDC W3 r041 在序列号 3QC0124C20000792 上 PASS_RETIRED；CI #61372 暴露 worker 禁止 alias hardlink，CI #61434 又证明 native package 阶段不应强制 build/package ELF hardlink，当前 recipe 已移除该重绑定路径，等待新候选平台验证

## 源码身份

- 官方发布包：`https://download.gnome.org/sources/json-glib/1.10/json-glib-1.10.8.tar.xz`
- 字节数：`1294096`
- SHA-256：`55c5c141a564245b8f8fbe7698663c87a45a7333c2a2c56f06f811ab73b212dd`

## 依赖闭包

- 直接依赖：`glib/2.88.3`、`proxy-libintl/0.5`
- GLib 的 OHOS/armv8 二进制闭包已解析到 `pcre2/10.47`、`libffi/3.5.2`、`zlib/1.3.2` 和 `proxy-libintl/0.5`。

## 当前适配

- 使用 `PkgConfigDeps` 生成目标依赖模块，并给 GLib 模块补齐宿主生成工具路径。
- Windows 主机交叉到 OHOS 时显式使用目标前缀 `/`。
- 配置前要求宿主存在 `pkg-config` 或 `pkgconf`；只有 `.pc` 文件而没有可执行查询工具时立即失败。
- 消费者程序运行前从 `self.build_folder` 解析并校验同一目录树内的绝对路径，再通过 `env="conanrun"` 注入运行时环境。
- 原生 POSIX OHOS worker 不再在 `package()` 阶段强制 build/package ELF 硬链接；版本化 ELF 由 Meson 安装副本直接保留，SONAME aliases 保留安装生成且已 `samefile()` 验证的符号链，不对 alias 强制创建 hardlink；test_package runtime staging 统一使用经过字节/mode 校验的副本，避免跨文件系统和 worker 能力差异成为非目标阻塞；Windows→OHOS 交叉路径继续保留普通文件物化。

## 已知失败与边界

1. 初次 `conan create` 未传 `--build=json-glib/1.10.8`，只证明根包尚无可复用二进制。
2. 后续配置进入 Meson 后因宿主找不到 `pkg-config` 而失败；这不表示 Conan 生成的 `.pc` 文件缺失。
3. 两次旧导出曾包含空字节；当前配方已独立验证空字节数为 0，旧日志不能代表当前候选。
4. 主机构建工具补齐只解决环境前置条件，不替代目标编译、17 项上游测试、消费者测试或真机 W3。
5. `local-r007` 已完成库本体交叉编译与打包，但消费者只收到裸 `-lintl`、未收到 `proxy-libintl` 库目录；修复为公开传递真实提供者，并移除错误的 `system_libs=["intl"]` 投影。
6. CI #60571（Buildbot 69302）确认仅保留 SONAME 符号链仍会在 native worker 的安装副本上以 RC 127 缺失 `libjson-glib-1.0.so.0`；当前候选改为保留构建/安装版本化库的 inode 身份，Windows-hosted OHOS RREV `30f7468b5a1980f3b86d332b64300853` 已本地 RC 0，USB HDC W3 r035 与 fresh upstream 17/17 通过，平台 CI 需再次确认。
6. CI #60571（Buildbot 69302）确认仅保留 SONAME 符号链仍会在 native worker 的安装副本上以 RC 127 缺失 `libjson-glib-1.0.so.0`；当前候选改为保留构建/安装版本化库的 inode 身份。随后 CI #61372 在 alias hardlink 阶段返回 `Operation not permitted`，证明 alias 目录项不能假设支持 hardlink；新候选只保留完整校验后的安装符号链，避免该非目标副作用。Windows-hosted OHOS RREV `1095fc754d0a4ff74a8f26aa9fe9c8a4` 已本地 RC 0，USB W3 successor 与平台 CI 需重新确认。
7. CI #61434 在 HEAD `525711869e65612133a6f6fc4ea4b86a2aad04b0` 的 `package()` 阶段拒绝 build/package 共享库 hardlink（两目录 `st_dev` 不同），而 17/17 上游测试已通过；该 worker 能力差异不应阻塞可用 package ELF。修复为移除 native package 硬链接重绑定，并让 test_package runtime staging 固定使用经过字节/mode 校验的副本。合并后的 Windows-hosted OHOS `local-win-r045-no-native-hardlink` 返回 RC 0，recipe RREV `b2ccb948a96ca4edd87b5837b28b3522`、PREV `a90dee4bf4f018466b9a28b5932d32f2`；USB HDC W3 r041 仍是上一候选证据，当前修复需新 successor 与 current-head CI 验证。

## 平台已知限制（上游测试运行期探测）

- glib 2.88.3 的子进程监视以 pidfd + `waitid (P_PIDFD)` 回收 `g_test_trap_subprocess()` 子进程；部分内核 pidfd 就绪后 `waitid` 始终返回空 `siginfo`，`g_child_watch_dispatch` 死循环刷屏 `pidfd signaled but pid … didn't exit`，`meson test` 永远无法汇总。CI #64135/#64145/#64149（三台不同 worker）均复现；WSL 冻结目录 17/17 不受影响。
- 处置：`patches/1.10.8-0001-probe-pidfd-reaping-before-node-trap-subprocess-tests.patch` 在 `node` 新增运行期能力探针（fork + pidfd_open + waitid 各一次，`G_OS_UNIX` 门控、无平台宏），探针判定回收失效时对 8 个 immutable trap-subprocess 用例 `g_test_skip()`。正常内核零行为差异；17 个测试单元与分母不变，SKIP 以 TAP 可见。

## 待验证清单

- Windows 原生 OHOS `conan create` 已完成，`local-win-r034-hardlink-alias` 返回 RC 0。
- fresh Meson 1.11.1 build 完成 55/55，实际枚举并执行 17 项，上游测试达到 17/17。
- 消费者编译、链接与目标运行通过。
- HarmonyOS PC 专属测试与唯一 USB HDC W3 r041 事务通过：3/3、7/7、1/1、8/8、12/12 receipts，launch_count=1，retire/post-retire PASS；r040 在 W3 传输前因冻结回读过滤漂移终止，未产生远端副作用，r041 重新完成精确传输与唯一 launch。
