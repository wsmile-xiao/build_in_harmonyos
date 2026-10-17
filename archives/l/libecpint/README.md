# libecpint

**libecpint** 是一个用于快速计算量子化学中**赝势（Effective Core Potential, ECP）积分**的 C++ 库：给定 ECP 基组与高斯壳层，计算单中心/双中心 ECP 积分及其一、二阶导数。支持最大角动量 L=5（`LIBECPINT_MAX_L` 可调），内置高斯-切比雪夫积分网格与 Bessel/Child-Watson 辅助函数，附带 pugixml 读取 XML 基组数据文件的接口。

- 上游：https://github.com/robashaw/libecpint
- 许可：MIT
- 构建系统：CMake ≥ 3.12（C++11）
- 本仓适配版本：1.0.7
