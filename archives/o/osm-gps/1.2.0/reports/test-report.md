# Test Report — osm-gps 1.2.0 (HarmonyOS PC aarch64 / OHOS, musl)

Status: PASS
RC: 0

## 消费者端到端测试（鸿蒙特有测试 = 1）

- 文件：`test_package/test_osm.c`
- 编译：clang + test_package 闭包（libosmgpsmap-1.0 / gtk3 / glib2 / libsoup 等），链接 `-losmgpsmap-1.0`。
- 执行：调用 `osm_gps_map_get_type()`（GObject 类型注册入口，经 `<osm-gps-map.h>` 暴露），headless 无 display 即可运行；注册成功时返回非 0 GType，进程退出码 0。
- 运行约束：经 `LD_PRELOAD=libsoup_gobject_shim.so` 中和 libsoup/2.74.3 静态内嵌 GLib 导致的 GType 双注册 abort（shim 须 `binary-sign-tool sign -selfSign 1` 签名方能被 OHOS loader 经 LD_PRELOAD 加载）。
- 实测平台：HarmonyOS PC aarch64（OHOS，musl libc），退出码 0 → 通过。

## 上游测试

- osm-gps-map 1.2.0 上游无 `make check` / 自动化测试套件（上游测试数 = 0）。
- 本消费者用例为 OHOS 专属验证（PR「鸿蒙特有测试」= 1）。

## 环境说明

- OHOS `/tmp` 只读，构建期产物落地于 `test_package/local-libs/`（已 gitignore，禁入 PR）。
- conan 安装包为只读，跨次运行先解除只读再 rmtree/copy，避免 `Operation not permitted`。
