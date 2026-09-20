# tinyusb — 开源嵌入式 USB 协议栈

## 概述

tinyusb（TinyUSB）是面向嵌入式系统的开源跨平台 USB 协议栈（MIT 许可），
提供设备侧（Device）与主机侧（Host）两套协议栈，覆盖 CDC/HID/MSC/MIDI/
VENDOR/AUDIO/VIDEO/NCM 等常用类，可在裸机与 FreeRTOS/Mynewt/Zephyr/RT-Thread
上运行。

**本仓库适配版本**：0.18.0（HarmonyOS PC aarch64 / musl）

## 功能概述

- 设备侧：`tud_*` 控制传输、类驱动（CDC-ACM、HID、MSC、MIDI、VENDOR…）、
  描述符框架、端点 FIFO（`tu_fifo`）
- 主机侧：`tuh_*` USB Host 栈、Hub 枚举、CDC/HID/MSC/VENDOR 主机类驱动
- 公共层：USB 描述符辅助函数（`tu_desc_len`/`tu_desc_type`）、
  类型无关环形缓冲（`tu_fifo`）、USBC（Type-C）状态机

## OHOS 适配要点

1. **tinyusb 是「源码库」，没有可独立使用的构建系统**：上游只有
   `src/CMakeLists.txt` 里的 `add_tinyusb(<target>)` 函数与 `src/tinyusb.mk`
   片段，两者都假定调用者已选好 MCU 家族并提供一个提供 `tusb_config.h` 的
   target。本包因此用 direct-cc 把配置与源文件清单钉死，产出可直接链接的
   `libtinyusb.a`。
2. **`src/portable/` 没有任何 Linux/OHOS 控制器后端**（只有 23 个裸机 MCU
   port 与一对 vendor 中立的 `template/`），OSAL 也仅 FreeRTOS/Mynewt/Zephyr/
   RT-Thread 四个端口。故本包走 `CFG_TUSB_MCU=OPT_MCU_NONE` +
   `CFG_TUSB_OS=OPT_OS_NONE`，并额外编入上游留给 MCU port 提供的
   `src/portable/template/{dcd,hcd}_template.c`。
3. **template 端口是不完整的**：`dcd_template.c` 只实现了
   `dcd_edpt_close_all()`，`dcd_edpt_close()`（`dcd.h:184`）与
   `dcd_int_handler()`（`usbd.h:76`，即 `tud_int_handler`）在模板端口内没有
   定义，属**强未定义符号**；`OPT_OS_NONE` 下还有 `tusb_time_millis_api()`
   （`tusb.h:173`）必须由应用提供。消费侧至少补齐这 3 个钩子，详见
   `0.18.0/test_package/test_tinyusb.c`。
4. **接上真实控制器的方式**：不改本配方，而是在自己的 `tusb_config.h` 里把
   `CFG_TUSB_MCU` 指向目标 port，用包内附带的 `src/` 源码重新编译；届时
   上述 3 个钩子会被真实 port 的实现取代。

## 依赖关系

- 编译依赖：无（零第三方依赖，仅需 libc）
- 运行依赖：无（系统 libc/ld）

## 参考链接

- 上游官网：https://www.tinyusb.org
- 上游仓库：https://github.com/hathach/tinyusb
- 本仓库版本笔记：`0.18.0/notes.md`
