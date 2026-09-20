# tinyusb 0.18.0 — HarmonyOS PC 适配笔记

## 1. 概览

| 项 | 值 |
|----|----|
| 上游 | https://www.tinyusb.org |
| 版本 | 0.18.0 |
| 源码 | `https://github.com/hathach/tinyusb/archive/refs/tags/0.18.0.tar.gz` |
| SHA256 | `e7fa1bd723213749a0362c79eaccc99e84c8adea8f0a63588c4e4812608b7aa9` |
| 构建 | direct-cc（直接驱动 clang，不经上游 CMake/Makefile） |
| 包类型 | static-library（`libtinyusb.a` + 整棵 `src/` 头/源树 + 默认 `tusb_config.h`） |
| 依赖 | 无（零 Conan 依赖，只依赖 libc） |

## 2. tinyusb 是"源码库"，没有可独立使用的构建系统

上游只提供两个构建入口，而它们都不是"库自己的构建"：

1. `src/CMakeLists.txt` 只有一个 `add_tinyusb(TARGET)` **函数**，把 23 个源文件
   追加到调用者的 target 上；末尾还会

   ```cmake
   if (NOT TARGET ${TINYUSB_CONFIG_TARGET})
     message(FATAL_ERROR "${TINYUSB_CONFIG_TARGET} target is not defined")
   endif()
   ```

   —— 即"你先给我一个提供 `tusb_config.h` 的 target"。
2. `src/tinyusb.mk` 同理，是给已有 Makefile 工程 `include` 的片段。

两条路径都假定调用者已经选好 MCU 家族并准备好控制器驱动。OHOS 上没有这样的
调用者，走上游 CMake 还要额外写 toolchain file、再自己造一个 `tinyusb_config`
target —— 绕了一圈回到同一个问题。因此本配方照 Samba/X11 系列在仓库里的既有
做法，用 direct-cc 把配置和源文件固定下来。

## 3. 配置决策

### 3.1 为什么是 `OPT_MCU_NONE` + `OPT_OS_NONE`

- `src/portable/` 下 23 个后端全部是裸机 MCU（nRF / STM32 / ESP / RP2040 /
  DWC2 / EHCI / OHCI …），**没有任何面向 Linux 或 OHOS 的控制器后端**；
  唯一"与设备无关"的是 `template/` 那一对空实现。
- `src/osal/` 只有 FreeRTOS / Mynewt / Zephyr / RT-Thread 四个端口，
  OHOS 不在其中。
- OHOS PC 上的 xHCI/DWC 控制器没有上游 port，写一个 port 属于超出本任务范围
  的新驱动开发；本包走 template 端口，产出一个**与具体控制器无关**的通用
  构建，把"接上真实控制器"这一步明确留给使用者（包内附带完整 `src/` 源码，
  改 `CFG_TUSB_MCU` 后可用自己的 `tusb_config.h` 重编）。

`files/tusb_config.h` 即这份默认配置：设备侧开 CDC/MSC/HID/MIDI/VENDOR，
**主机侧关闭**，其余类（net 需要 lwip、audio/video 需要逐类子选项）关闭。

主机侧必须关闭，原因是 template 那一对端口**不对称**（详见 §5.1）：

```
src/portable/template/dcd_template.c:  bool dcd_init(...) { return true;  }   // 可用的空实现
src/portable/template/hcd_template.c:  bool hcd_init(...) { return false; }   // 待填的骨架
```

设备角色能在这套 template 端口上初始化成功，主机角色不能：`CFG_TUH_ENABLED=1`
时 `tusb_init()` 会在 `usbh.c` 的 `TU_ASSERT(hcd_init(rhport, rh_init))` 处
返回 false —— 设备栈明明已经起来了，整个 `tusb_init()` 却报失败。所以默认配置
只开设备侧，主机侧的类契约（`CFG_TUH_CDC/HID/MSC`）保留，供将来补上 HCD 的
使用者直接启用。

### 3.2 关闭的类仍然参与编译

`class/audio/audio_device.c`、`class/net/*.c` 等即使 `CFG_*=0` 也照常进源文件
列表 —— 上游 CMake 就是这么做的，关闭时它们编译成空 TU，不影响归档，也让
使用者改配置重编时不必再动文件列表。

## 4. 源文件清单

上游客服 `add_tinyusb()` 的 23 个文件（`src/CMakeLists.txt`），外加 2 个
template 端口文件（上游把它们留给 MCU port 提供，OHOS 没有 port）：

```
tusb.c common/tusb_fifo.c
device/usbd.c device/usbd_control.c
class/audio/audio_device.c class/cdc/cdc_device.c
class/dfu/dfu_device.c class/dfu/dfu_rt_device.c
class/hid/hid_device.c class/midi/midi_device.c class/msc/msc_device.c
class/net/ecm_rndis_device.c class/net/ncm_device.c
class/usbtmc/usbtmc_device.c class/vendor/vendor_device.c class/video/video_device.c
host/usbh.c host/hub.c
class/cdc/cdc_host.c class/hid/hid_host.c class/msc/msc_host.c
class/vendor/vendor_host.c
typec/usbc.c
portable/template/dcd_template.c portable/template/hcd_template.c   ← OHOS 追加
```

`class/bth/bth_device.c`、`class/cdc/cdc_rndis_host.c` 不在上游 CMake 列表内，
本包同样不编，与上游两条构建路径保持一致。

清单与上游逐行对齐，但默认配置只开设备侧，所以上面 `host/` 与 `*_host.c` 这
几行在默认配置下都编译成空 TU（它们整体被 `CFG_TUH_ENABLED` 包住）。留着是
为了让有 HCD 的使用者改一个宏就能从包内源码重编出主机栈，不必再动文件列表。

## 5. 踩坑与解决

### 5.1 主机栈在 OHOS 上必然初始化失败：`hcd_template.c` 的 `hcd_init()` 恒返回 false

初始配方把 `CFG_TUSB_RHPORT0_MODE` 设成 DEVICE、`CFG_TUSB_RHPORT1_MODE` 设成
HOST 并 `CFG_TUH_ENABLED=1`，构建全绿、两个上游 Unity 用例也全过，但
`test_package` 一跑就挂：

```
FAIL[9]: tusb_init() failed with OPT_MCU_NONE/OPT_OS_NONE
```

定位过程（本地复现 + 给 `TU_ASSERT` 打桩）：`tusb_init()` →
`tusb_rhport_init(0, NULL)` → 设备栈初始化成功 → 主机栈分支
`TU_ASSERT(tuh_rhport_init(...))` → `usbh.c:421`：

```c
  TU_ASSERT(hcd_init(rhport, rh_init));   // src/host/usbh.c:421
```

而 `src/portable/template/hcd_template.c:47`：

```c
bool hcd_init(uint8_t rhport, const tusb_rhport_init_t* rh_init) {
  (void) rhport; (void) rh_init;
  return false;      // ← 上游故意留成 false
}
```

也就是说这不是 OHOS 的编译/移植问题，而是**上游 template 端口的设计**：设备侧
的 `dcd_template.c` 返回 true（可用的空实现，栈能跑起来只是没有真实控制器），
主机侧的 `hcd_template.c` 返回 false（纯粹的骨架，作者假定使用者一定会替换
它）。两边语义不对称，只看文件名会误以为可以对称使用。

结论与处置：

- tinyusb 0.18.0 的 `src/portable/` 里没有任何 Linux/OHOS 主机控制器后端
  （`dwc2`/`ehci`/`ohci`/`synopsys` … 全是 SoC 专用），OHOS PC 的 xHCI 没有
  上游 port，写一个 HCD 属于新驱动开发，超出本任务范围；
- 因此默认配置**只开设备侧**（`CFG_TUH_ENABLED=0`，且不定义
  `CFG_TUSB_RHPORT1_MODE`，避免 `TUH_OPT_RHPORT` 被置上）；
- `test_package` 用两条断言把这个性质钉住：断言 4 证明 `tusb_init()` 确实能
  成功，断言 7 证明包内 `tusb_config.h` 的 `CFG_TUH_ENABLED` 为 0 且设备栈
  处于 inited 状态。谁把默认配置改回开主机侧，CI 立刻红。

### 5.2 `dcd_int_handler` / `dcd_edpt_close` 强未定义（链接期）

`src/portable/template/dcd_template.c` 只写了 `dcd_edpt_close_all()`：

```
src/device/dcd.h:184:  void dcd_edpt_close(uint8_t rhport, uint8_t ep_addr);
src/device/usbd.h:76:  extern void dcd_int_handler(uint8_t rhport);
src/device/usbd.h:80:  #define tud_int_handler   dcd_int_handler
```

声明在，定义不在 —— 模板端口就是故意留白让使用者补的。这两个是**强**未定义
符号，消费侧不补齐就链接失败。本包在 `test_package/test_tinyusb.c` 里补上，
并把它写进知识草稿：这是 template 端口与真实 MCU port 的接口契约，换成真实
port 后这两处定义会与之冲突，是一道天然的"端口是否被换掉"的哨兵。

### 5.3 `tusb_time_millis_api()` 必须由应用提供

`CFG_TUSB_OS=OPT_OS_NONE` 时 `tusb.c:53` 直接调用 `tusb_time_millis_api()`
（`tusb.h:173` 声明、非 weak），OHOS 侧没有 OSAL 端口可以代劳，所以这是第三
个必须由应用补齐的钩子。

### 5.4 Ceedling 的 include 路径

`test/unit-test/project.yml`：

```yaml
:paths:
  :source:
    - ../../src/**
```

Ceedling 会把 `src/**` 的**每个子目录**都加进 include 搜索路径，于是上游用例
写的是 `#include "tusb_fifo.h"`（`test_fifo.c:31`）而不是
`#include "common/tusb_fifo.h"`。手工编译时只给 `-Isrc` 会
`fatal error: 'tusb_common.h' file not found`。`conanfile.py` 的
`_src_include_dirs()` 枚举 `src/` 全部子目录来复现 Ceedling 的搜索路径。

库自身的 `.c` 一律写相对 `src/` 的全路径（`#include "common/tusb_common.h"`），
所以**只需要** `-Isrc`；这条只有跑上游用例时才需要。

### 5.5 两条 `#warning`

- `tusb_option.h:529`：`CFG_TUD_NET is renamed to CFG_TUD_ECM_RNDIS`。
  0.18.0 起旧的 `CFG_TUD_NET` 只作回填，故直接改用
  `CFG_TUD_ECM_RNDIS` / `CFG_TUD_NCM`。
- `common/tusb_mcu.h:562`：`TUP_DCD_ENDPOINT_MAX is not defined for this
  MCU, default to 8`。`OPT_MCU_NONE` 不在 MCU 表里，上游会警告后默认 8；在
  `tusb_config.h` 里显式钉成同一个值 8，语义不变而构建输出零警告。

## 6. 上游测试

上游 `test/unit-test` 是 **Ceedling 0.31.1** 工程（入口
`test/unit-test/ceedling`，内部跑 `vendor/ceedling` 里 vendored 的 Ruby gem，
默认任务 `test:all`），用 Unity 断言 + CMock 桩。

| 测试 | 类型 | 处置 |
|------|------|------|
| `test/common_func`（`test_common_func.c`，1 用例 / 33 断言） | Unity，无 mock | build() 内编译 + 运行 |
| `test_fifo`（`test_fifo.c`，14 用例 / 61 断言） | Unity，无 mock | build() 内编译 + 运行 |
| `test/device/usbd`（`test_usbd.c`，5 用例） | Unity + **CMock** | 排除：`#include "mock_dcd.h"` / `"mock_msc_device.h"` 由 Ceedling 调 CMock 生成，OHOS worker 无 Ruby |
| `test/device/msc`（`test_msc_device.c`，1 用例） | Unity + **CMock** | 排除：同上（`#include "mock_dcd.h"`） |

两个可执行文件用**源码树内自带的 Unity**（
`test/unit-test/vendor/ceedling/vendor/unity/src/unity.c`）链接，runner 由本包
提供（`files/unity_runner_test_common_func.c` / `files/unity_runner_test_fifo.c`）
—— Ceedling 平时会自动生成这个 main，这里用等价的 20 行替代，不需要 Ruby。
构建产物只在 build 阶段使用，**不进包**。

上游另有两条不在 `test/unit-test` 之下的测试通道，均无法在 OHOS CI worker 上
执行，已在 body「验证结果」中逐条说明：`test/fuzz/`（libFuzzer 入口 5 个 +
`device/{cdc,msc,net,net_ncm}` 语料，需要 `-fsanitize=fuzzer`）与 `test/hil/`
（Python 硬件在环，必须插真实 USB 板子）。

## 7. 验证记录

本地用 OHOS native SDK（clang 15.0.4 + `--target=aarch64-linux-ohos`）预验证：

- 25 个源文件在 `-Wall -Wextra` 下**零错误零警告**编译通过，`libtinyusb.a`
  成档（154,790 字节）；
- `llvm-nm` 显示归档解析完内部引用后，除 `memcpy`/`memmove`/`memset` 外只剩
  19 个未定义符号，全部是"必须由应用提供"的钩子（见 §8）；
- `unity.c` + 两个 runner + 两个上游用例文件**均链接成功**；
- `test_package/test_tinyusb.c` 消费者程序**链接成功**。

后来在 x86-64 gcc 11.4 上把整条链完整跑了一遍（同一份源码 + 同一份
`tusb_config.h`）：

```
$ ./test_common_func  1 Tests 0 Failures 0 Ignored  OK   (rc=0)
$ ./test_fifo        14 Tests 0 Failures 0 Ignored  OK   (rc=0)
$ ./test_tinyusb
tinyusb ...  (num 1800)
tu_fifo round-trip ok (count=0)
tusb_init() ok, tud_inited=1
descriptor packing ok (dev=18 cfg=9 itf=9 ep=7)
tud_task() x1000 non-blocking ok (0.000s)
device stack up: tusb_inited=1 tud_inited=1 CFG_TUH_ENABLED=0
RESULT PASS                                              (rc=0)
```

§5.1 那条 `hcd_init()` 恒返回 false 的坑就是靠这套本地复现定位的。

CI（OHOS aarch64 原生 worker）中 `conan create` 会真正编译并**运行**两个
Unity 用例与 test_package 消费者测试。

## 8. 链接期未定义符号（归档内部解析之后）

| 符号 | 来源 | 谁提供 |
|------|------|--------|
| `memcpy` `memmove` `memset` | libc | libc |
| `tusb_time_millis_api` | `tusb.c`（OPT_OS_NONE 时间基准） | 应用 |
| `dcd_int_handler` | `usbd.h:76` / `tud_int_handler` | 应用（template 端口留白） |
| `dcd_edpt_close` | `dcd.h:184` / `usbd.c:1447` | 应用（template 端口留白） |
| `tud_descriptor_*_cb` ×3、`tud_hid_*_cb` ×3、`tud_msc_*_cb` ×6 | 已启用的设备类（CDC/MSC/HID/MIDI/VENDOR） | 应用 |

`test_package/test_tinyusb.c` 里还留了一个 `tuh_hid_report_received_cb`：默认
配置关掉主机栈后它**不再被引用**（`hid_host.c` 编译成空 TU），保留它纯粹是
给将来启用主机栈的使用者留个现成的钩子，属于消费者侧代码，不影响库。表里
其余弱符号（`tud_cdc_*_cb`、`tud_msc_*_cb` 的可选回调、`usbd_app_driver_get_cb`
等）上游本身声明成 weak，不补也能链接。

## 9. test_package 断言清单

`test_package/test_tinyusb.c` 里 7 组断言，失败时以不同退出码（2…18）区分，
便于 CI 日志定位：

| # | 断言 | 失败退出码 |
|---|------|-----------|
| 1 | `TUSB_VERSION_*` == 0.18.0 | 2 |
| 2 | `tu_fifo` 写入 32 字节 / 读出 32 字节 / 内容一致 / 读空后为空 | 3, 4, 5, 6 |
| 3 | `tu_desc_type()` == 0x02、`tu_desc_len()` == 0x09 | 7, 8 |
| 4 | `tusb_init()` 在 OPT_MCU_NONE/OPT_OS_NONE 下成功 | 9 |
| 5 | **鸿蒙特有**：aarch64 上描述符结构体打包（device=18 / config=9 / interface=9 / endpoint=7，`offsetof(bInterval)==6`） | 10, 11, 12, 13, 14 |
| 6 | **鸿蒙特有**：1000 次 `tud_task()` 不阻塞（<2s，用 OHOS `clock_gettime` 计），且无控制器事件时 `tud_mounted()` 为假 | 15, 16 |
| 7 | **鸿蒙特有**：包内默认配置 `CFG_TUH_ENABLED==0`（主机栈关闭，见 §5.1），且 `tusb_inited()` / `tud_inited()` 均为真 | 17, 18 |

第 5 条针对的是 OHOS 用 clang 15 + bionic(musl) 与裸机 MCU 工具链对齐/padding
规则不同：描述符是跨设备线格式，`TU_ATTR_PACKED` 一旦失效会**静默**产出畸形
描述符（编译链接全绿、设备枚举失败），必须显式断言尺寸与偏移。

第 6 条针对的是 OHOS 没有 tinyusb 的 OSAL 端口：栈必须以"无 OS 等待原语"的
方式运行，用真实单调时钟给 `tud_task()` 设时间预算，退化回阻塞实现即可观测。

第 7 条针对的是 OHOS 没有主机控制器后端（§5.1）：消费者 `-I` 本包
`include/` 拿到的就是这份 `tusb_config.h`，所以 `CFG_TUH_ENABLED` 的取值是
包对外的可观测契约。断言 4 与断言 7 互为表里 —— 前者证明设备栈真能起来，
后者证明"起来的是设备栈而不是主机栈"，两者一起把 §5.1 的结论锁死，防止有人
"顺手"把默认配置改回 `CFG_TUH_ENABLED=1` 而不被 CI 拦住。

## 10. 卸载/回退

- 本包不修改上游任何源码（`patches_applied: []`），回退 = 删除
  `archives/t/tinyusb/0.18.0/`；
- 接入真实控制器时的正确做法不是改本配方，而是在自己的 `tusb_config.h` 里把
  `CFG_TUSB_MCU` 指向目标 port，并用包内附带的 `src/` 重新编译 —— 届时
  §5.2 的两个 template 钩子会被真实 port 的定义取代，`test_package` 的同名
  定义需一并去掉（这也是"端口是否被换掉"的天然哨兵）；
- 要恢复主机功能，必须自己实现 `hcd_init()` / `hcd_int_enable()` … 一整套
  HCD 接口（见 §5.1），再把 `CFG_TUH_ENABLED` 与 `CFG_TUSB_RHPORT1_MODE`
  打开；只翻这两个宏而不补 HCD，`tusb_init()` 会直接返回 false；
- 升级时需重新核对：`src/portable/` 是否新增了 Linux/OHOS 后端、`src/osal/`
  是否新增端口、`CFG_TUD_NET` 一类改名宏、以及 `tusb_config.h` 是否需要新增
  `CFG_*`/`TUP_*` 键。
