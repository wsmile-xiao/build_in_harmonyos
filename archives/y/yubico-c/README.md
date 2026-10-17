# yubico-c

yubico-c（上游包名 ykclient / yubico-c-client）是 Yubico 的 C 客户端库，用于通过 YubiCloud 验证 YubiKey OTP。

## OHOS 适配

- 采用 autotools（configure + make）构建，产出静态 `libykclient.a` 和 `ykclient` CLI 工具。
- 依赖 `libcurl/8.5.0`（ohpcd 制品仓）。
- config.guess（2014）不识别 HarmonyOS，显式指定 `--build/--host=aarch64-unknown-linux-ohos`。
- E114：configure 中 `umask 077` 在 HMDFS 上产生不可写 setgid 目录，已在配方中修复。
- `make -j1` 避免 HMDFS jobserver fifo EPERM。
- 消费者测试直接调用 `ykclient_global_init`、`ykclient_check_version`、`ykclient_set_client_hex` 等真实 API。

## 参考

- 上游仓库：https://github.com/Yubico/yubico-c-client
- 上游发布页：https://developers.yubico.com/yubico-c-client/Releases/
- 许可证：BSD-2-Clause
