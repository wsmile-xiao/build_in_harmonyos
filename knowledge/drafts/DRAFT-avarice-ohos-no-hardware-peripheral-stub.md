# DRAFT-avarice-ohos-no-hardware-peripheral-stub: OHOS 无硬件环境的外设库依赖 stub 绕过

> **Contributor**: xiao921924 | **Status**: Draft | **Updated**: 2026-08-22
> **Severity**: 2 | **Category**: harmonyos / hardware / stub / peripheral / autotools / libusb
> **Source**: avarice 2.14-svn427 HarmonyOS PC adaptation, PR #6154

## 错误特征

```text
jtag2usb.cc: 错误: usb.h: No such file or directory
undefined reference to `usb_get_string_simple'
undefined reference to `usb_open'
undefined reference to `usb_bulk_read'
libusb-1.0 not found
```

## 现象

avarice（AVR JTAG ICE ↔ GDB 调试接口）依赖 libusb-0.1（USB 接口——`libusb_open`/
`usb_get_string_simple` 等 15 个 `usb_*` API）。OHOS 无硬件环境（无 JTAG ICE/USB
调试器等外设）：

1. `configure` 的 `AC_CHECK_LIB([usb], [usb_get_string_simple])` 检查**不硬失败**
   （无 `AC_MSG_ERROR`——configure 能过）；
2. 但编译 `jtag2usb.cc`（`#include <usb.h>`——15 个 `usb_*` API）需要外设库的
   头文件 + 链接符号；
3. libusb-compat 无配方/不在制品仓——无法直接依赖。

## 与现有知识的关系

- 无现成 E-entry 直接覆盖"OHOS 无硬件环境下外设库依赖 stub 绕过"场景——本草稿
  待 promote 至 `knowledge/graph/E0XX.kv` + `doc/E0XX.md`。

## 根因

OHOS 沙箱/无硬件环境——库依赖硬件外设库（libusb-0.1——USB 接口）时，configure
依赖检查可过但编译/链接需要外设 API——无硬件环境下外设库依赖无法满足。

## 解决方法

**stub 绕过**（R9/R34 合规——如实记录 stub——不伪造功能）：

1. 生成 stub 头（声明外设 API——libusb-0.1 的 15 个 `usb_*`）+ stub 实现
   （返回 -1/0——无硬件——功能不实际使用）；
2. `CPPFLAGS -I stub`（编译源文件找到 stub 头）；
3. 编译 stub 对象 + 链接追加（`make LIBS='... {stub_dir}/usb_stub.o'`——链接满足
   `usb_*` 符号）。

```python
stub_dir = os.path.join(build_folder, "stub"); os.makedirs(stub_dir, exist_ok=True)
# stub usb.h: typedef struct usb_device usb_dev_handle; + usb_init/usb_find_busses/
#   usb_find_devices/usb_get_busses/usb_open/usb_close/usb_get_string_simple/
#   usb_bulk_read/usb_bulk_write/usb_claim_interface/usb_release_interface/
#   usb_resetep/usb_set_configuration/usb_error/usb_daemon 声明
# stub usb_stub.c: 各函数返回 0/-1（无硬件）
clang -c stub/usb_stub.c -I stub -o stub/usb_stub.o
CPPFLAGS += -I stub_dir          # 编译源文件找到 stub 头
make LIBS='... {stub_dir}/usb_stub.o'   # 链接满足 usb_* 符号
```

## 验证

- 构建对比：直接依赖外设库（configure 检查失败/编译缺头——`usb.h No such file`）
  vs stub 方案（stub 头 + stub 实现——编译链接通过——bin 生成——如实记录 stub
  不伪造功能）。

## 适用场景

OHOS 上适配依赖硬件外设库（USB/串口/GPIO/调试器等）的工具/库（调试器、烧录器、
传感器工具等）——无硬件环境——configure 依赖检查可过但编译/链接需要外设 API——
stub 方案可复用。

## 禁止做法

- 不要伪造外设功能实现（R9）——stub 必须如实记录、功能不实际使用。
- 不要在无硬件环境下宣称外设功能可用（R34）。
