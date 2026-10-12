# libnice 0.1.21 HarmonyOS PC 适配记录

## 构建目标

- 目标平台：HarmonyOS PC 6.0，aarch64（Conan `OHOS/armv8`）
- 构建系统：Meson；HarmonyOS SDK Clang 15
- 默认产物：静态 libnice；运行依赖 GLib（shared）和 OpenSSL
- 构建保留核心 ICE/STUN 与 `stund`、`stunbdc`，关闭 GStreamer、GUPnP、introspection、GTK 文档和示例；启用上游测试
- 源码来自官方 `https://nice.freedesktop.org/releases/libnice-0.1.21.tar.gz`，SHA256：`72e73a2acf20f59093e21d5601606e405873503eb35f346fa621de23e99b3b39`

## 适配内容

- Conan 配方通过 MesonToolchain 配置 aarch64 本机构建，并从 Conan 依赖注入 Meson 所需工具路径和 GLib `glib-mkenums` 元数据。
- `test_package` 使用 `nice.pc` 编译真实 C consumer；程序创建 `NiceAgent` 并添加 ICE stream。
- `test_ohos_stun_loopback.sh` 在 HarmonyOS 上实际启动 `stund`，再用 `stunbdc` 发送本机 IPv4 UDP Binding Request 并检查 `Mapped address` 响应。
- 上游测试清点见 `test_package/MANIFEST.yml`：69 个上游测试项分布于 41 个 Meson 测试目标（33 个 GLib 注册用例，加 36 个独立测试目标）；设备缺少 coturn，因此其中 6 个 TURN 注册用例未执行。最终设备 W3 结果写入 `reports/w3-local-ci.log`。

### 对话 #1

- 2026-10-11：按需求选择核心库、`stund` 和 `stunbdc`；关闭 GStreamer、GUPnP 与 introspection，并为两个命令行工具登记软件级 `commands.json`。
- 2026-10-11：在 `MALLOC_PERTURB_=84` 下复现上游随机传输测试的多一字节问题，定位到 EWOULDBLOCK 返回值 `-1` 被误当作已接受字节数；归一为零后，设备上的 1 MiB 文件逐字节比较通过。

## 发现与知识

- ✅ HarmonyOS 队列满时 `pseudo_tcp_socket_send()` 可返回 `-1`（EWOULDBLOCK，接受 0 字节）。上游随机文件测试原样把 `-1` 纳入计数，并用 `wlen - len` 回退，实际会多回退一字节并重复上一字节；补丁先将负值归一为 0，再更新计数和文件位置。知识草稿：E545。
- ✅ 静态 GLib 的 libintl 链接问题与知识条目 E123 相符，因此此配方依赖 shared GLib。
- ✅ consumer 运行验证显式包含 Conan 依赖库目录，确认完整运行时链接闭包；相关背景见 E499。

## 验证记录

- 2026-10-11，HarmonyOS PC 6.0 aarch64（HarmonyOS SDK Clang 15）：官方 W3 本地 CI 使用 Conan 创建并运行 `libnice/0.1.21`，结果通过；41/41 Meson 测试目标返回通过。按测试项统计为 63 PASS、6 SKIP、0 FAIL（共 69 项）；6 个 TURN 用例因设备未安装 coturn 而由上游测试程序提前跳过。清点口径为 5 个 GLib 测试文件的 33 个注册用例，加 36 个独立目标各自的 1 个测试项；独立目标中包含此前漏列的 `random/test.c`。原始日志：`reports/w3-local-ci.log`。全局 `finish` 未完成：W5 因仓库既有知识图谱校验问题及发布就绪材料缺失返回 partial；这不改变该包 W3 的结果。
- Conan consumer 编译并运行成功，实际创建 `NiceAgent` 和 ICE stream 1；验证报告：`reports/conan-verify-report.md`，创建日志：`reports/conan-create.log`。
- HarmonyOS 专项 IPv4 UDP STUN loopback 通过：最近一次设备 W3 中启动 `stund`，`stunbdc` 向 `127.0.0.1:58690` 发送 Binding Request，收到映射地址 `127.0.0.1:35727`。这是设备上的真实 UDP 请求/响应测试，不是纯断言。
- 最终补丁还在 `MALLOC_PERTURB_=84` 下复跑 1 MiB PseudoTCP 随机传输：退出码 0，发送和接收文件均为 1,048,576 字节且逐字节相同。
- 官方 `.ci-result.json` 的日志 SHA256 与 `reports/w3-local-ci.log` 相符。W3 收尾中的 `stund`/`stunbdc` `--version`/`--help` 冒烟项给出非阻塞警告；二者的真实运行由上述 loopback 行为测试覆盖。完整 `finish` 的 W5 仓库级检查和发布就绪检查仍未通过，不能据此声称整体 finish 成功。

---

**编译结束**: 2026-10-11
**最终状态**: built
