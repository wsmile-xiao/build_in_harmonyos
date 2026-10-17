# serialdv - AMBE3000 数字语音编解码串口/UDP 接口库

## 简介
serialdv 是一个小型 C++ 库（源于 OpenDV 项目的精简接口），用于通过串口或
AMBE-over-UDP 与 AMBE3000 芯片（DVSI ThumbDV 等硬件狗）在 packet mode 下
交互，完成数字语音（D-Star、DMR、YSF、P25 等）音频帧与 AMBE 帧的编解码。
库按"一对象一设备一线程"设计，每次 encode/decode 是一次原子 query/reply 事务。

## 功能
- `DVController`：设备打开/PRODID 识别、速率切换（13 种 AMBE 速率）、
  增益设置、单帧 `encode()` / `decode()` 与 MBE 帧长查询
- 传输后端：`SerialDataController`（termios 串口，支持 FTDI 低延迟 ioctl）、
  `UDPDataController`（AMBE-over-UDP 服务端，`ip:port` 形式设备名）、
  `DummyDataController`（占位）
- `dvtest` 命令行工具：读入 8 kS/s S16LE 音频，经设备编码再解码输出

## OHOS 适配
- 构建系统：CMake（上游 `add_library(serialdv SHARED ...)`）
- **零补丁**：OHOS SDK sysroot 已提供全部所需头文件/常量——
  `linux/serial.h`（`struct serial_struct`）、`TIOCGSERIAL/TIOCSSERIAL`
  （`aarch64-linux-ohos/bits/ioctl.h`）、`ASYNC_LOW_LATENCY`
  （`linux/tty_flags.h`）、`B230400/B460800`（`bits/termios.h`）
- 交付产物：`lib/libserialdv.so`（SONAME `libserialdv.so`，由配方注入
  `-Wl,-soname,libserialdv.so`）+ `include/serialdv/*.h` + `bin/dvtest`
- 运行依赖：无第三方库；实际功能需要 AMBE3000 硬件或 AMBE-over-UDP 服务端，
  无硬件时库可正常加载，`dvtest -h` 可运行
- 上游无自动化测试套件（无 tests/ 目录、CMakeLists 无 `enable_testing()`/
  `add_test()`；`dvtest` 为需真实设备的工具，samples/ 仅为输入样本），
  适配后补全消费者 API 回归测试（`test_package/test_serialdv.cpp`，59 断言）

## 依赖关系
```
serialdv/1.1.5 (cmake, C++11)
└─ 无第三方依赖（仅 POSIX termios / BSD socket + libc++）
```

## 参考资料
- 上游仓库：https://github.com/f4exb/serialDV
- 源码包：https://github.com/f4exb/serialDV/archive/refs/tags/v1.1.5.tar.gz
- 适配记录：`1.1.5/notes.md`

## 许可证
GPL-3.0-or-later（见上游 LICENSE）
