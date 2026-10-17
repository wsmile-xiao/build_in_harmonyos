# libad9361-iio - AD9361 收发器辅助库

## 简介
libad9361-iio 是 Analog Devices AD9361 射频收发器的辅助库，提供与时钟链规划、FIR 滤波器设计相关的纯算法函数，配套多芯片同步等设备功能。

## 功能
- 射频时钟链速率计算（ad9361_calculate_rf_clock_chain 等纯计算 API）
- FIR 滤波器设计（ad9361_generate_fir_taps，Remez 设计算法）
- 多芯片同步 / FMComms5 相位同步（需硬件）
- 基带速率配置辅助

## 上游
- https://github.com/analogdevicesinc/libad9361-iio （tag v0.3）
