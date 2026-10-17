/*
 * test_package consumer test for tinyusb/0.18.0 on HarmonyOS PC.
 *
 * 这个程序同时是"最小可用消费者"：它只提供 OHOS 上 tinyusb 必须由应用提供的
 * 三类东西 ——
 *   1) tusb_time_millis_api()：OHOS 没有 tinyusb 的 OSAL 端口（上游只提供
 *      FreeRTOS / Mynewt / Zephyr / RT-Thread），CFG_TUSB_OS=OPT_OS_NONE 下
 *      时间基准必须由应用给出（tusb.h:173 声明、tusb.c 调用）。
 *   2) dcd_int_handler() / dcd_edpt_close()：OPT_MCU_NONE 的 template 端口
 *      (src/portable/template/dcd_template.c) 只实现了 dcd_edpt_close_all()，
 *      这两个强符号在模板端口里根本没有定义，链接期必须由应用补齐。
 *   3) 本应用启用的设备类的回调（descriptor / msc / hid）。
 *
 * 每个断言失败时返回不同的退出码，便于在 CI 日志里定位。
 */

#include "tusb.h"

#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

/* ------------------------------------------------------------------
 * 1) OPT_OS_NONE 的时间基准
 * ------------------------------------------------------------------ */
static uint32_t s_fake_ms = 0;

uint32_t tusb_time_millis_api(void) { return s_fake_ms; }

/* ------------------------------------------------------------------
 * 2) template 端口未提供的两个强符号
 * ------------------------------------------------------------------ */
void dcd_int_handler(uint8_t rhport) { (void) rhport; }
void dcd_edpt_close(uint8_t rhport, uint8_t ep_addr)
{
  (void) rhport;
  (void) ep_addr;
}

/* ------------------------------------------------------------------
 * 3) 设备描述符与类回调
 * ------------------------------------------------------------------ */
static const uint8_t desc_device[] = {
  18, 0x01, 0x00, 0x02, 0x00, 0x00, 0x00, 64,
  0x86, 0x1a, 0x00, 0x10, 0x00, 0x01,
  0x00, 0x01, 0x00, 0x00
};

uint8_t const *tud_descriptor_device_cb(void) { return desc_device; }
uint8_t const *tud_descriptor_configuration_cb(uint8_t index)
{
  (void) index;
  return NULL;
}
uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid)
{
  (void) index;
  (void) langid;
  return NULL;
}

uint8_t const *tud_hid_descriptor_report_cb(uint8_t i)
{
  (void) i;
  return NULL;
}
uint16_t tud_hid_get_report_cb(uint8_t i, uint8_t id, hid_report_type_t t,
                               uint8_t *b, uint16_t l)
{
  (void) i; (void) id; (void) t; (void) b; (void) l;
  return 0;
}
void tud_hid_set_report_cb(uint8_t i, uint8_t id, hid_report_type_t t,
                           uint8_t const *b, uint16_t l)
{
  (void) i; (void) id; (void) t; (void) b; (void) l;
}

int32_t tud_msc_read10_cb(uint8_t lun, uint32_t lba, uint32_t off, void *buf,
                          uint32_t n)
{
  (void) lun; (void) lba; (void) off; (void) buf; (void) n;
  return -1;
}
int32_t tud_msc_write10_cb(uint8_t lun, uint32_t lba, uint32_t off, uint8_t *buf,
                           uint32_t n)
{
  (void) lun; (void) lba; (void) off; (void) buf; (void) n;
  return -1;
}
int32_t tud_msc_scsi_cb(uint8_t lun, uint8_t const scsi[16], void *buf, uint16_t n)
{
  (void) lun; (void) scsi; (void) buf; (void) n;
  return -1;
}
bool tud_msc_test_unit_ready_cb(uint8_t lun) { (void) lun; return false; }
void tud_msc_inquiry_cb(uint8_t lun, uint8_t v[8], uint8_t p[16], uint8_t r[4])
{
  (void) lun; (void) v; (void) p; (void) r;
}
void tud_msc_capacity_cb(uint8_t lun, uint32_t *bc, uint16_t *bcs)
{
  (void) lun;
  *bc = 0;
  *bcs = 512;
}

void tuh_hid_report_received_cb(uint8_t a, uint8_t b, uint8_t const *c, uint16_t d)
{
  (void) a; (void) b; (void) c; (void) d;
}

/* ------------------------------------------------------------------ */

static int fail(int code, const char *what)
{
  printf("FAIL[%d]: %s\n", code, what);
  return code;
}

static double seconds_since(const struct timespec *t0)
{
  struct timespec t1;
  clock_gettime(CLOCK_MONOTONIC, &t1);
  return (double) (t1.tv_sec - t0->tv_sec)
       + (double) (t1.tv_nsec - t0->tv_nsec) / 1e9;
}

int main(void)
{
  int rc;

  /* 断言 1 — 版本常量：确认构建用的源码树就是 0.18.0（退出码 2） */
  if (TUSB_VERSION_MAJOR != 0 || TUSB_VERSION_MINOR != 18
      || TUSB_VERSION_REVISION != 0) {
    return fail(2, "TUSB_VERSION_* != 0.18.0");
  }
  printf("tinyusb %s (num %d)\n", TUSB_VERSION_STRING, TUSB_VERSION_NUMBER);

  /* 断言 2 — tu_fifo 环形缓冲读写往返（退出码 3..6） */
  {
    tu_fifo_t ff;
    static uint8_t storage[64];
    uint8_t in[32], out[64];

    tu_fifo_config(&ff, storage, sizeof(storage), 1, false);
    for (int i = 0; i < 32; i++) {
      in[i] = (uint8_t) (i * 7);
    }

    if (tu_fifo_write_n(&ff, in, 32) != 32) {
      return fail(3, "tu_fifo_write_n returned != 32");
    }
    memset(out, 0, sizeof(out));
    if (tu_fifo_read_n(&ff, out, 32) != 32) {
      return fail(4, "tu_fifo_read_n returned != 32");
    }
    if (memcmp(out, in, 32) != 0) {
      return fail(5, "tu_fifo round-trip content mismatch");
    }
    if (!tu_fifo_empty(&ff) || tu_fifo_count(&ff) != 0) {
      return fail(6, "tu_fifo not empty after full drain");
    }
    printf("tu_fifo round-trip ok (count=%u)\n", tu_fifo_count(&ff));
  }

  /* 断言 3 — USB 描述符长度/类型辅助函数（退出码 7..8） */
  {
    static const uint8_t cfg[] = { 0x09, 0x02, 0x00, 0x00, 0x00, 0x00 };

    if (tu_desc_type(cfg) != 0x02) {
      return fail(7, "tu_desc_type != 0x02 (CONFIGURATION)");
    }
    if (tu_desc_len(cfg) != 0x09) {
      return fail(8, "tu_desc_len != 0x09");
    }
  }

  /* 断言 4 — 在 OPT_MCU_NONE/OPT_OS_NONE 下完成栈初始化（退出码 9）。
   *
   * 这里能成功，前提是主机栈关闭：上游 src/portable/template/hcd_template.c
   * 的 hcd_init() 恒返回 false（纯空模板），只要 CFG_TUH_ENABLED=1，
   * tusb_init() 就会在 usbh.c 的 TU_ASSERT(hcd_init(...)) 处失败 ——
   * 哪怕设备栈本身已经初始化成功。本包的默认 tusb_config.h 因此只开设备侧，
   * 断言 7 再显式钉住这一点。
   */
  if (!tusb_init()) {
    return fail(9, "tusb_init() failed with OPT_MCU_NONE/OPT_OS_NONE");
  }
  printf("tusb_init() ok, tud_inited=%d\n", tud_inited());

  /* 断言 5（鸿蒙特有）— OHOS aarch64 上 USB 描述符结构体的内存布局必须与
   * USB 线格式完全一致。描述符是跨设备字节流，tinyusb 靠 TU_ATTR_PACKED
   * 保证无填充；OHOS 用 clang 15 + bionic(musl)，对齐/padding 规则与裸机
   * MCU 工具链不同，一旦打包被破坏，设备发出的描述符会静默畸形（枚举失败但
   * 编译链接全绿），因此必须显式断言。（退出码 10..14）
   */
  if (sizeof(tusb_desc_device_t) != 18) {
    return fail(10, "sizeof(tusb_desc_device_t) != 18");
  }
  if (sizeof(tusb_desc_configuration_t) != 9) {
    return fail(11, "sizeof(tusb_desc_configuration_t) != 9");
  }
  if (sizeof(tusb_desc_interface_t) != 9) {
    return fail(12, "sizeof(tusb_desc_interface_t) != 9");
  }
  if (sizeof(tusb_desc_endpoint_t) != 7) {
    return fail(13, "sizeof(tusb_desc_endpoint_t) != 7");
  }
  if (offsetof(tusb_desc_endpoint_t, bInterval) != 6) {
    return fail(14, "offsetof(tusb_desc_endpoint_t, bInterval) != 6");
  }
  printf("descriptor packing ok (dev=%u cfg=%u itf=%u ep=%u)\n",
         (unsigned) sizeof(tusb_desc_device_t),
         (unsigned) sizeof(tusb_desc_configuration_t),
         (unsigned) sizeof(tusb_desc_interface_t),
         (unsigned) sizeof(tusb_desc_endpoint_t));

  /* 断言 6（鸿蒙特有）— OHOS 没有 tinyusb 的 OSAL 端口，栈必须以
   * OPT_OS_NONE 的"无 OS 等待原语"方式运行：tud_task() 在没有任何控制器
   * 事件（template 端口不会产生 attach/enum 事件）时必须立即返回，
   * 不能阻塞在内核对象上。用 OHOS 的 clock_gettime(CLOCK_MONOTONIC) 给出
   * 时间预算，超过 2 秒即判为退化成了阻塞实现。（退出码 15..16）
   */
  {
    struct timespec t0;
    int i;

    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (i = 0; i < 1000; i++) {
      tud_task();
      s_fake_ms++;
    }
    if (seconds_since(&t0) > 2.0) {
      return fail(15, "1000x tud_task() took > 2s (OS wait primitive leaked in)");
    }
    if (tud_mounted()) {
      return fail(16, "tud_mounted() true without a controller event");
    }
    printf("tud_task() x1000 non-blocking ok (%.3fs)\n", seconds_since(&t0));
  }

  /* 断言 7（鸿蒙特有）— 包内默认配置必须把主机栈关掉，且设备栈确实起来了。
   *
   * OHOS 没有 tinyusb 的主机控制器后端（src/portable/ 下 dwc2/ehci/ohci/…
   * 全是 SoC 专用，xHCI 无上游 port），template 端口的 hcd_init() 又恒返回
   * false。于是"主机栈开着"在 OHOS 上不是一个可选项而是一个必失败项：只要
   * CFG_TUH_ENABLED=1，断言 4 就会挂。这条断言从消费者角度把默认配置的性质
   * 钉死——消费者 -I 本包 include/ 拿到的就是这份 tusb_config.h，所以
   * CFG_TUH_ENABLED 是否为 0 是包对外的可观测契约，不是内部实现细节。
   * （退出码 17..18）
   */
#if CFG_TUH_ENABLED
  return fail(17, "shipped tusb_config.h has CFG_TUH_ENABLED=1; template HCD "
                  "hcd_init() returns false so tusb_init() can never succeed");
#endif
  if (!tusb_inited() || !tud_inited()) {
    return fail(18, "device stack not up after a successful tusb_init()");
  }
  printf("device stack up: tusb_inited=%d tud_inited=%d CFG_TUH_ENABLED=%d\n",
         (int) tusb_inited(), (int) tud_inited(), (int) CFG_TUH_ENABLED);

  rc = 0;
  printf("RESULT PASS\n");
  return rc;
}
