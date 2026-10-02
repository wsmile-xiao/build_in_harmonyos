# langford 0.0.20130228 适配笔记

## 上游构成

`langford_0.0.20130228.orig.tar.bz2`（根目录 `langford_driver/`）包含三部分：

| 部分 | 文件 | 是否可构建 |
|---|---|---|
| 内核模块 | `langford.c` / `langford.h` | 否（OHOS 无 `linux/pci.h` 内核 API、无 loadable module） |
| 用户态工具 | `langford_util.cpp` / `langford_adc_util.cpp` / `langford_spi.cpp` | 是 |
| 设备程序 | `libs/fsynth.cpp`（ADF4351）/ `libs/lmh6521.cpp`（LMH6521 VGA） | 是 |

## 构建

- 构建系统：手写 Makefile（`g++ -ansi`），无三方依赖。配方直接用 clang++ 编译，`-std=gnu++98`。
- 内核模块 `langford.c` 无法在 OHOS 编译（需要 Linux 内核构建系统与 PCIe 驱动 API），
  按 Debian 的 `langford-dkms` 拆分口径单独排除，不在本包产物内。
- 链接器：`llvm-ar` 打包 `liblangford_spi.a`。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/langford_util` | 通过 ioctl 读写板卡各引脚 |
| `bin/langford_adc_util` | ADC1210S125 SPI 编程 |
| `bin/langford_rf_fsynth` | ADF4351 频率合成器编程（`libs/fsynth.cpp`） |
| `bin/langford_rx_rf_bb_vga` | LMH6521 增益控制（`libs/lmh6521.cpp`） |
| `lib/liblangford_spi.a` | `LangordSpiWrite()` SPI 助手库 |
| `include/langford_ioctl.h`、`langford_spi.h` | 公共头文件 |

## 测试

上游无测试套件 → 上游 N=0。`test_package` 中：

- `test_langford.sh` 16 项断言：四个工具的无参 usage / 缺设备 / 非法通道 / 非法增益路径；
- `test_spi.cpp` 编译链接 `liblangford_spi.a`，验证 ioctl 常量与 `LangordSpiWrite()` 在非法 fd 上返回非零。

合计消费者用例 17 项。
