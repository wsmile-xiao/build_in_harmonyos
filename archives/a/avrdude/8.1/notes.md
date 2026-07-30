# avrdude 8.1 编译笔记

## 编译环境
- 平台: HarmonyOS aarch64
- 编译器: clang 15.0.4

## 编译过程

- 使用 CMake 静态构建，禁用当前仓库中不可用的可选外部 USB、GPIO、SPI 和
  libserialport 适配器。
- `HAVE_LIBSERIALPORT=OFF` 仅关闭可选第三方适配器；上游内置的
  `ser_posix.c` 串口后端及 Arduino、STK500 等串口协议仍参与构建。
- 上游 `tools/test-avrdude` 的 2 个无硬件 dryrun 场景通过。
- OHOS Bash 无法保留上游计时函数使用的嵌套文件描述符；补丁仅将耗时
  采集改为 Bash `SECONDS`，测试命令、输出及退出状态保持不变。
- `test_package` 验证版本输出，并选择 Arduino 编程器访问一个不存在的设备，
  确认程序已进入 POSIX 串口打开路径。真实烧录仍需要开发板和串口设备，
  不适合作为无硬件 CI 门禁。

## 最终状态
- 状态: built
- 验证: 上游测试 2/2（100%），新增测试 2/2（100%）
