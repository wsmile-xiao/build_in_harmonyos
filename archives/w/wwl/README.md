# wwl — Maidenhead 网格定位工具

`wwl`（"World Wide Locator"）是一个把业余无线电常用的 **Maidenhead 网格定位** 换算为距离与方位角的小工具，由 Diane Bruce（VA3DB）于 2007 年重写。

同一份程序以 `argv[0]`（可执行文件名）区分两种模式：

- **`wwl home_locator dx_locator`**：计算两个网格方格之间的 **距离（QRB，单位 km）** 与 **方位角（azimuth，单位度）**，例如：
  ```
  $ wwl fn25di jo55ei
  qrb: 5810 kilometers, azimuth: 46 degrees
  ```
- **`locator locator`**：反算单个网格方格的经纬度，例如：
  ```
  $ locator FN25di
  Locator    : FN25DI
  Coordinates: Long: (W) -75.75 Lat : (N) 45.3333
  ```

若只给出 4 位网格（如 `jo55`），程序会自动补足为 `JO55AA`。

## OHOS 适配要点

- **单文件 + 手写 Makefile**：无 `configure`，直接 `make CC=<clang> CFLAGS="-Wall -O2" -j1`，仅链接 `-lm`。
- **HTTPS 源约束**：上游只在明文 HTTP 主机发布（`http://www.db.net/downloads/`）。为满足 `conandata.yml` 不得出现明文 `http://` 的规则，使用 Debian 的同版本 `.orig.tar.gz`（HTTPS）并固定 sha256。
- **`locator` 分发**：程序按可执行文件 basename 选择模式，因此打包时复制出真实的 `bin/locator` 可执行文件并保持执行位，而不是依赖符号链接。
- **无上游测试**：上游 Makefile 仅 `all`/`install`/`release`/`clean`，没有 `check`/`ctest`；由 `test_package` 的消费者断言补齐（覆盖 `wwl(1)` 手册中的全部算例）。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/wwl` | 距离/方位角计算 |
| `bin/locator` | 网格方格 → 经纬度 |
| `share/man/man1/wwl.1` | wwl 手册 |
| `share/man/man1/locator.1` | locator 手册 |

## 参考资料

- 上游发布：<https://www.db.net/downloads/>（Debian 包 `wwl`）
- 作者：Diane Bruce (VA3DB) `<db@FreeBSD.ORG>`
- 许可证：作者自定的宽松许可（保留版权声明即可，禁止以 GPL 再许可）
