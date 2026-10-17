# langford — Per Vices Noctar（原 Phi）IQ 解调板控制工具

`langford` 是 Per Vices 公司为 **Noctar**（早期称 **Phi**）软件无线电 IQ 解调板提供的
主机侧软件。上游包含一个 Linux 内核驱动（`langford.c`）和一组用户态工具：

- **`langford_util`**：通过 `/dev/langford` 字符设备的 ioctl 读写板卡各引脚。
- **`langford_adc_util`**：编程板载 ADC1210S125（SPI 位敲）。
- **`langford_rf_fsynth`**：编程 ADF4351 频率合成器（`libs/fsynth.cpp`）。
- **`langford_rx_rf_bb_vga`**：编程 LMH6521 可变增益放大器（`libs/lmh6521.cpp`）。
- **`liblangford_spi.a`**：`LangordSpiWrite()` SPI 位敲助手库（`langford_spi.cpp`）。

## 用法

```sh
langford_util /dev/langford N21at0            # 读引脚
langford_util /dev/langford N3GAIN 12         # 写引脚
langford_adc_util /dev/langford A IntRef 3    # ADC A 内部参考 3 dB
langford_rf_fsynth /dev/langford rx 100000000 # RX 调到 100 MHz
langford_rx_rf_bb_vga /dev/langford 0 20      # I 通道增益 20 dB
```

## OHOS 适配要点

- **内核模块排除**：`langford.c`/`langford.h` 是 Linux PCIe/DMA 内核模块，OHOS 无
  loadable kernel module 与 `linux/pci.h` 设备 API，按 Debian `langford-dkms` 的拆分口径
  单独排除；本包只提供用户态工具与 SPI 助手库。
- **无三方依赖**：上游用手写 Makefile + `g++ -ansi`；配recip用 clang++、`-std=gnu++98` 直接编译。
- **HTTPS 源**：上游只在明文 HTTP（pervices.com）发布，改用 Debian 同版本 `.orig.tar.bz2`
  （HTTPS）并固定 sha256。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/langford_util` | 引脚 ioctl 工具 |
| `bin/langford_adc_util` | ADC SPI 编程 |
| `bin/langford_rf_fsynth` | ADF4351 频率合成器编程 |
| `bin/langford_rx_rf_bb_vga` | LMH6521 增益控制 |
| `lib/liblangford_spi.a` | SPI 助手库 |
| `include/langford_ioctl.h`、`langford_spi.h` | 头文件 |

## 参考资料

- 上游主页：<http://www.pervices.com/>
- 许可证：GPL-3.0-or-later
