# libsigrok 0.5.2 — 当前 Conan 适配记录

本版使用 sigrok 官方源码归档及已发布的 GLib、libzip、zlib、Check。2026-06 的手动安装记录不适用于本次 Conan 候选，尤其不能继续宣称 60 多个 USB 驱动或预编译包已发布。

- `configure` 使用当前目标编译器证实的 OHOS triplet。CI worker 不一定安装识别该 tuple 的新版 `config.sub`；优先使用已验证的安装版本，缺失时仅对本次构建副本的 2018 年 `autostuff/config.sub` 增加精确 `linux-ohos` 模式并复验，不修改共享工具链。
- 目标机无 `/dev/bus/usb`，`libusb_init()` 返回 `LIBUSB_ERROR_IO`，使上游 76 个 Check 用例中 46 个在 `sr_init()` 阶段失败。本候选使用上游 `--without-libusb`，保留 demo/非 USB 功能；USB 采集不在适配声明内。
- 已发布依赖中个别 Libtool `.la` 含 `libdir='//lib'`、`dependency_libs=//lib/...`。配方仅在自己的构建目录复制并修复链接输入，不改共享 Conan 缓存。
- Check 0.15.2 的测试进程优先使用 `TEMP`，随后可能落到只读 `/tmp`；配方把 `TEMP` 设为本轮构建私有目录，且对其 `ck_assert_msg` 格式参数做一处精准的构建副本兼容修复，不删除测试。
- `tests/main` 是 Libtool shell 包装器，真正的 ELF 是 `tests/.libs/main`，需签名后由 `make check` 执行。原始日志中 12 个 suite 合计 76 个 Check case，不能仅报告 1 个测试可执行文件。配方核对 `100%: Checks: 76, Failures: 0, Errors: 0`。
- 公开头文件包含 GLib 类型，Conan 要求对 GLib 声明传递头文件/库属性；否则生产者构建成功而安装包消费者找不到 `glib.h`。

CI #70527 暴露 worker 缺少新版 `config.sub`，故加入构建副本回退路径。针对性回退测试 `BUNDLED_CONFIG_SUB_FALLBACK_PASS`；修正后的真机事务 `libsigrok-w3-20261003T211200Z` 12 阶段通过，上游 76/76、消费者 1/1，Conan 原始日志 SHA-256 `cf56fff52cf1d01e97cff6413c54b1e41543062ad7f097f07327dc98d5153dc8`。真机优先使用已有新版 `config.sub`，回退分支由独立测试覆盖。
