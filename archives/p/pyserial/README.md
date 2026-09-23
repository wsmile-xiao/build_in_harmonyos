# pyserial

pyserial is a pure-Python serial port extension for Windows, macOS, Linux, BSD, and other Python platforms.

## 功能概述

- 提供 `serial.Serial` 和 `serial_for_url()` 串口 API
- 支持 `loop://`、RFC 2217、socket 等 URL handler
- 提供 `pyserial-miniterm` 与 `pyserial-ports` 命令行工具
- 支持串口参数、超时、线程化读写和 RS-485 配置

## OHOS 适配

- 以 Conan `python-require` noarch 包交付，不包含 C/C++ 编译产物。
- Python 模块安装到 Conan 包的 `lib/python/site-packages`，运行环境自动设置 `PYTHONPATH`，不绑定构建机 Python 小版本。
- 当前设备上游 PTY 测试中的调制解调器 ioctl 受权限限制，相关失败已记录在版本测试报告；核心 `loop://` 回环和消费者测试通过。

## 依赖关系

- 编译依赖：Python 3.x、Conan 2.x
- 运行依赖：Python 3.x
- Conan 依赖：无

## 参考资料

- 官网/源码仓库：<https://github.com/pyserial/pyserial>
- v3.5 release：<https://github.com/pyserial/pyserial/releases/tag/v3.5>
