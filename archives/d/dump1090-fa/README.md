# dump1090-fa

FlightAware 维护的 Mode-S/ADS-B 报文解码器，可从 SDR（RTL-SDR/BladeRF/HackRF/LimeSDR）接收 1090MHz 信号并解码航班信息。

## 命令

- `dump1090`: 主解码器（ADS-B/Mode-S 报文解码、网络输出）
- `view1090`: 简易交互式视图
- `faup1090`: 从文件回放解码
- `starch-benchmark`: DSP 基准测试

## 版本

- 8.0 (built)

## 构建说明

- 构建系统: Makefile（纯 make，无 configure）
- 编译器: clang
- 依赖: ncurses/6.5（交互界面需要，制品仓静态包）
- 特殊处理: OHOS 下 Makefile 不设置 LIBS_CURSES，配方显式传入 `-lncursesw` 及 ncurses 头文件路径
