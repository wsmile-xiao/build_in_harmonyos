# xfel

全志（Allwinner）SoC 的轻量级 **FEL 工具**，由 xboot 项目（Jianjun Jiang）维护。
把 SoC 置为 FEL 模式（上电时拉低特定引脚）后经 USB OTG 连接，即可在**没有任何
存储介质**的情况下对 SoC 做初始烧录与调试。

- 上游：<https://github.com/xboot/xfel>
- 文档：<https://xfel.xboot.org/guide/intro/>
- 许可证：MIT

## 包内产物

| 路径 | 说明 |
|------|------|
| `bin/xfel` | 命令行工具 |
| `share/xfel/99-xfel.rules` | 上游 udev 规则（授权 USB 设备 `1f3a:efe8`；OHOS 无 udev，随包留档） |
| `licenses/LICENSE` | 上游 MIT 许可证 |

## 命令行接口

```
xfel version                                        - Show chip version
xfel hexdump <address> <length>                     - Dumps memory region in hex
xfel dump <address> <length>                        - Binary memory dump to stdout
xfel read32 <address>                               - Read 32-bits value from device memory
xfel write32 <address> <value>                      - Write 32-bits value to device memory
xfel read <address> <length> <file>                 - Read memory to file
xfel write <address> <file>                         - Write file to memory
xfel exec <address>                                 - Call function address
xfel reset                                          - Reset device using watchdog
xfel sid                                            - Show sid information
xfel jtag                                           - Enable jtag debug
xfel ddr [type]                                     - Initial ddr controller with optional type
xfel sign <public-key> <private-key> <file>         - Generate ecdsa256 signature file for sha256 of sid
xfel spinor                                         - Detect spi nor flash
xfel spinor erase <address> <length>                - Erase spi nor flash
xfel spinor read <address> <length> <file>          - Read spi nor flash to file
xfel spinor write <address> <file>                  - Write file to spi nor flash
xfel spinand                                        - Detect spi nand flash
xfel spinand erase <address> <length>               - Erase spi nand flash
xfel spinand read <address> <length> <file>         - Read spi nand flash to file
xfel spinand write <address> <file>                 - Write file to spi nand flash
xfel spinand splwrite <split-size> <address> <file> - Write file to spi nand flash with split support
xfel extra [...]                                    - The extra commands
```

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| libusb | 1.0.27 | 强制第三方（动态链接；OHOS 无系统同名库） |

## 使用

```bash
conan install --requires=xfel/1.3.5 -pr:h=<ohos-aarch64 profile>
```

设备访问需要 root 权限（`/dev/bus/usb`），且需内核 usbfs 支持。在容器或无 USB
访问权限的环境中，`libusb_init()` 会失败，xfel 会打印 `ERROR: Can't initialize
libusb` 并以 rc=255 退出（不会崩溃）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.3.5 | built | 首次适配；1 个补丁（libusb_init 返回值检查），无上游自动化测试 |
