# tinyusb 0.18.0：无自带构建系统的「源码库」适配范式 + template 端口的强未定义钩子契约

## 场景一：先判断一个包是「可构建的库」还是「源码库」

tinyusb 上游**没有**任何可独立调用的构建入口：

- `src/CMakeLists.txt` 里只有一个 `add_tinyusb(TARGET)` **函数**，把 23 个源
  文件 append 到**调用者**的 target 上；末尾还会
  ```cmake
  if (NOT TARGET ${TINYUSB_CONFIG_TARGET})
    message(FATAL_ERROR "${TINYUSB_CONFIG_TARGET} target is not defined")
  endif()
  ```
  —— 即"你先给我一个提供 `tusb_config.h` 的 target"。
- `src/tinyusb.mk` 同理，是给已有 Makefile 工程 `include` 的片段。

两条路径都假定调用者已经选好 MCU 家族、准备好控制器驱动。OHOS 上没有这样
的调用者：走上游 CMake 还要额外写 toolchain file、自己造一个 `tinyusb_config`
target，绕一圈回到同一问题。

**判定信号（在 source() 之后、写 build() 之前扫一遍）**：
- `CMakeLists.txt` 顶层只有 `add_*(TARGET)` 之类函数、没有
  `project()`/`add_library()`；
- 存在 `*.mk` 片段式构建文件而非完整 Makefile；
- `#include "tusb_config.h"` 这类**用户配置头**是硬需求；
- 源码里大量 `#if CFG_xxx`，编译期行为由外部宏决定。

命中即按 **direct-cc** 处理：把配置与源文件清单在配方里钉死，产出单一静态库，
并把整棵源码树随包发运，让使用者改配置后能自行重编。

## 场景二：MCU 端口类的库——`/portable` 里没有你的平台怎么办

`src/portable/` 下 23 个后端**全是裸机 MCU**（nRF/STM32/ESP/RP2040/DWC2/
EHCI/OHCI…），没有任何 Linux/OHOS 控制器后端；`src/osal/` 只有 FreeRTOS/
Mynewt/Zephyr/RT-Thread 四个端口。OHOS 不在其中，且 OHOS PC 上位 xHCI/DWC，
写一个新 port 属于**新驱动开发**，超出「适配三方库」的范围。

正确做法是走 **vendor 中立的 template 端口**（`src/portable/template/`），
产出一个**与具体控制器无关**的通用构建：

```
CFG_TUSB_MCU=OPT_MCU_NONE
CFG_TUSB_OS =OPT_OS_NONE
+ src/portable/template/dcd_template.c
+ src/portable/template/hcd_template.c   ← 这两个文件不在上游 CMake 列表里，
                                           上游留给 MCU port 提供
```

## 场景三：template 端口的「留白」是强未定义符号——这是接口契约也是哨兵

`dcd_template.c` 只实现了 `dcd_edpt_close_all()`。以下两个只有声明、没有定义：

| 符号 | 声明处 | 性质 |
|------|--------|------|
| `dcd_edpt_close` | `src/device/dcd.h:184` | 强未定义，模板端口故意留白 |
| `dcd_int_handler` | `src/device/usbd.h:76`（`#define tud_int_handler dcd_int_handler`） | 同上 |

`OPT_OS_NONE` 下 `tusb.c:53` 还会直接调用 `tusb_time_millis_api()`
（`tusb.h:173` 声明、**非 weak**），OHOS 侧没有 OSAL 端口可以代劳。

⇒ 消费侧**至少**要补 3 个钩子（外加自己启用类的回调）。实测归档解析完内部
引用后，`libtinyusb.a` 中除 `memcpy/memmove/memset` 外只剩 19 个未定义符号，
全部是"必须由应用提供"的钩子。

**这 3 个钩子同时是一道天然的哨兵**：一旦接入真实控制器 port，真实 port 会
定义 `dcd_edpt_close`/`dcd_int_handler`，此时消费侧的重名定义**必然冲突**。
换言之，"链接是否报重定义"就是"端口是否已被换掉"的探测器——换成真实 port 时
须同步删掉消费侧的同名定义。

## 场景四：Ceedling 工程的 include 搜索路径还原

上游用例 `test/unit-test/project.yml` 写的是：
```yaml
:paths:
  :source:
    - ../../src/**
```
Ceedling 会把 `src/**` 的**每一个子目录**都加进 include 搜索路径，所以上游用例
写的是 `#include "tusb_fifo.h"`（`test_fifo.c:31`）而非 `"common/tusb_fifo.h"`。
脱离 Ceedling 手工编译时只给 `-Isrc` 会 `fatal error: 'tusb_common.h' file not
found`。复现方式：`os.walk(src/)` 枚举全部子目录逐一 `-I`。

注意区分：**库自身的 `.c` 一律写相对 `src/` 的全路径**（`#include
"common/tusb_common.h"`），所以编译库只需要 `-Isrc`；只有跑上游用例时才需要
补全所有子目录。

另：该工程是 **Ceedling 0.31.1**（`test/unit-test/ceedling` 是几十字节的 shell
包装，内部跑 vendored Ruby gem）。4 个测试文件中 `test_common_func.c` 与
`test_fifo.c` 不使用任何 CMock 桩，可直接用源码树内自带的 Unity
（`test/unit-test/vendor/ceedling/vendor/unity/src/`）配一个 20 行 runner
（本包提供 `files/unity_runner_*.c`）编译运行；`device/usbd` 与
`device/msc` 则 `#include "mock_dcd.h"` 等 CMock 生成物，需 Ruby 才能产出，
OHOS 构建 worker 上不可执行。

## 场景五：两条编译期 `#warning` 的正名

- `tusb_option.h:529`：0.18.0 起 `CFG_TUD_NET` 被拆分为
  `CFG_TUD_ECM_RNDIS` / `CFG_TUD_NCM`，沿用旧名只会打一条 `#warning` 再回填。
  直接用新名。
- `common/tusb_mcu.h:562`：`TUP_DCD_ENDPOINT_MAX is not defined for this MCU,
  default to 8`。`OPT_MCU_NONE` 不在 MCU 表里，上游警告后默认 8；在
  `tusb_config.h` 里显式 `#define TUP_DCD_ENDPOINT_MAX 8`，语义不变而构建输出
  零警告。
