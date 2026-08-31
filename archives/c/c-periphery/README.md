# c-periphery

用户态 Linux 外设 I/O 接口 C 库（vsergeev/c-periphery），HarmonyOS PC 适配归档。

- 上游：https://github.com/vsergeev/c-periphery
- 许可证：MIT
- 构建：CMake（>=3.19），另有原生 Makefile 可选
- 能力：GPIO（cdev v2/v1/sysfs 自动探测）、LED、PWM、SPI、I2C、MMIO、Serial 接口，
  编译为 `libperiphery.a` / `libperiphery.so`；纯 C99，零外部依赖（仅标准 C 库 + Linux 接口）

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.5.0 | built | 2026-08-30 | OHOS aarch64 首次适配，上游测试 8 项编译链接验证（执行需真实外设） |

## 适配要点

- 纯 C99 零依赖，无需补丁；CMake 自动探测 `linux/gpio.h` 决定 GPIO cdev v2/v1/sysfs 支持级别
- 上游 `tests/*.c` 8 个测试程序全部需要真实外设硬件（串口/GPIO/I2C/SPI/PWM/LED/MMIO），
  CI 环境不可执行：conan create 中仅做编译链接验证（HMBS 标记如实上报 skipped），逐文件申报于
  `2.5.0/test_package/MANIFEST.yml`
- 消费者验证：`2.5.0/test_package/test_periphery.c`（版本 API + serial 错误路径，4 断言，无硬件可复现）
- 库类型（无可执行文件产物），无需 commands.json（R38）
