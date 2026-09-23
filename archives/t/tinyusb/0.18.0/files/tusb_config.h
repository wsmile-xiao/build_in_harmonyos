/*
 * tusb_config.h — HarmonyOS PC 默认配置
 *
 * tinyusb 是"源码库"：它没有独立的构建系统，所有编译期行为都由使用者的
 * tusb_config.h 决定。要在 OHOS 上产出一个可以直接链接的 libtinyusb.a，
 * 就必须把这一份配置固定下来，它就是本包的"默认配置"。
 *
 * 关键决策：
 *   - CFG_TUSB_MCU = OPT_MCU_NONE：tinyusb 0.18.0 的 src/portable/ 下没有任何
 *     面向 Linux/OHOS 的控制器后端（只有 template/ 这一对空实现）。OHOS PC
 *     上的 xHCI/DWC 控制器没有上游 port，因此这里走 template 端口，产出一个
 *     "与具体控制器无关"的通用构建。需要真实控制器时，使用者在自己的
 *     tusb_config.h 里改 CFG_TUSB_MCU 并重编包内附带的 src/ 即可。
 *   - CFG_TUSB_OS = OPT_OS_NONE：上游只提供 FreeRTOS / Mynewt / Zephyr /
 *     RT-Thread 四个 OSAL 端口，没有 OHOS 端口。OPT_OS_NONE 让栈以"裸机"方式
 *     运行，时间基准由使用者实现 tusb_time_millis_api() 提供。
 *   - 只开设备侧（CFG_TUD_ENABLED=1），主机侧关闭（CFG_TUH_ENABLED=0）：
 *     template 那一对端口是不对称的 —— dcd_template.c 的 dcd_init() 返回
 *     true（可用的空实现），hcd_template.c 的 hcd_init() 返回 false（纯粹的
 *     待填模板）。开主机侧会让 tusb_init() 整个失败，详见文件末尾 HOST
 *     CONFIGURATION 段。
 *
 * 设备侧开启的类：CDC / MSC / HID / MIDI / VENDOR。其余类（net 需要 lwip，
 * audio/video 需要逐类 CFG_TUD_AUDIO_* / CFG_TUD_VIDEO_* 子选项）保持关闭 ——
 * 对应的 .c 仍然参与编译，只是在关闭时不产生代码，不会影响归档。
 * 主机侧的类契约保持与上游默认一致，供将来补上 HCD 的使用者直接启用。
 */

#ifndef _TUSB_CONFIG_H_
#define _TUSB_CONFIG_H_

#ifdef __cplusplus
extern "C" {
#endif

//--------------------------------------------------------------------
// COMMON CONFIGURATION
//--------------------------------------------------------------------
#ifndef CFG_TUSB_MCU
#define CFG_TUSB_MCU            OPT_MCU_NONE
#endif

#define CFG_TUSB_OS             OPT_OS_NONE

#ifndef CFG_TUSB_DEBUG
#define CFG_TUSB_DEBUG          0
#endif

#ifndef CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_SECTION
#endif

#ifndef CFG_TUSB_MEM_ALIGN
#define CFG_TUSB_MEM_ALIGN      __attribute__ ((aligned(4)))
#endif

// 只声明设备角色（rhport0）。CFG_TUSB_RHPORT1_MODE 这里**故意不定义**：
// 一旦定义成 HOST，TUH_OPT_RHPORT 就会被置上，tusb_init() 会去初始化主机栈，
// 而主机栈在 OPT_MCU_NONE 下必然失败 —— 见下方 HOST CONFIGURATION 的说明。
#define CFG_TUSB_RHPORT0_MODE   (OPT_MODE_DEVICE | OPT_MODE_FULL_SPEED)

//--------------------------------------------------------------------
// DEVICE CONFIGURATION
//--------------------------------------------------------------------
#define CFG_TUD_ENABLED         1
#define CFG_TUD_MAX_SPEED       OPT_MODE_FULL_SPEED
#define CFG_TUD_ENDPOINT0_SIZE  64

#define CFG_TUD_CDC             1
#define CFG_TUD_MSC             1
#define CFG_TUD_HID             1
#define CFG_TUD_MIDI            1
#define CFG_TUD_VENDOR          1
#define CFG_TUD_AUDIO           0
#define CFG_TUD_DFU             0
#define CFG_TUD_DFU_RUNTIME     0
#define CFG_TUD_USBTMC          0
#define CFG_TUD_VIDEO           0
// 0.18.0 起 CFG_TUD_NET 被拆成 CFG_TUD_ECM_RNDIS / CFG_TUD_NCM；沿用旧名会让
// tusb_option.h 打一条 #warning 再回填，故直接用新名。
#define CFG_TUD_ECM_RNDIS       0
#define CFG_TUD_NCM             0

// OPT_MCU_NONE 不在 common/tusb_mcu.h 的 MCU 表里，上游对"未知 MCU"会
// #warning 并回落到 8。这里显式钉成同一个值：语义与上游默认一致，构建输出
// 不再有这条 #warning。
#define TUP_DCD_ENDPOINT_MAX    8

#define CFG_TUD_CDC_RX_BUFSIZE  512
#define CFG_TUD_CDC_TX_BUFSIZE  512
#define CFG_TUD_MSC_BUFSIZE     512
#define CFG_TUD_HID_EP_BUFSIZE  64
#define CFG_TUD_MIDI_RX_BUFSIZE 64
#define CFG_TUD_MIDI_TX_BUFSIZE 64
#define CFG_TUD_VENDOR_RX_BUFSIZE 64
#define CFG_TUD_VENDOR_TX_BUFSIZE 64
#define CFG_TUD_TASK_QUEUE_SZ   100

//--------------------------------------------------------------------
// HOST CONFIGURATION
//--------------------------------------------------------------------
// ⚠️ 主机栈在 OHOS 上**不能**开启，这不是取舍而是硬事实：
//
// 上游 src/portable/template/hcd_template.c 的 hcd_init() 是
//     bool hcd_init(uint8_t rhport, const tusb_rhport_init_t* rh_init) { return false; }
// —— 它是写给 MCU port 作者抄的**空模板**，故意返回 false（而设备侧的
// dcd_template.c 返回 true）。tinyusb 0.18.0 的 src/portable/ 下没有任何
// Linux/OHOS 主机控制器后端（dwc2/ehci/ohci/… 全是 SoC 专用），OHOS PC 上的
// xHCI 没有上游 port。因此只要 CFG_TUH_ENABLED=1，tusb_init() 就会在
// usbh.c 的 TU_ASSERT(hcd_init(rhport, rh_init)) 处失败并返回 false ——
// 设备栈明明初始化成功了，整个 tusb_init() 却报失败。
//
// 所以默认配置只开设备侧；需要主机功能的使用者必须自己实现 hcd_init() 等
// 一整套 HCD 接口（包内附 src/，可自行重编），届时把这里改成 1 即可。
#define CFG_TUH_ENABLED         0
#define CFG_TUH_MAX_SPEED       OPT_MODE_FULL_SPEED
#define CFG_TUH_MAX3421         0
#define CFG_TUH_DEVICE_MAX      4
#define CFG_TUH_ENUMERATION_BUFSIZE 256

#define CFG_TUH_CDC             1
#define CFG_TUH_HID             1
#define CFG_TUH_MSC             1
#define CFG_TUH_VENDOR          0
#define CFG_TUH_CDC_FTDI        0
#define CFG_TUH_CDC_CP210X      0
#define CFG_TUH_CDC_CH34X       0

#ifdef __cplusplus
}
#endif

#endif /* _TUSB_CONFIG_H_ */
