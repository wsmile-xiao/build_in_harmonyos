# console-bridge

日志转发层：把日志调用转交给可替换的 OutputHandler。

ROS 生态里用来解耦「产生日志」与「输出日志」的薄层。库本身不决定日志去哪，
只负责把调用连同级别转交给当前注册的 handler，宿主程序再按自己的方式落盘或上屏。

mplib 的 so 依赖 `libconsole_bridge.so.1` 即本系列（1.0.x）。

- 上游：https://github.com/ros/console_bridge
- 许可证：BSD-3-Clause
- 鸿蒙 PC 适配版本：见各版本目录
