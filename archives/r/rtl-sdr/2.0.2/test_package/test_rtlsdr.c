/*
 * rtl-sdr 2.0.2 消费者用例（平台 rule12：真跑端到端业务流程）。
 *
 * CI 与开发机都没有 RTL2832U 电视棒，真实枚举恒为 0 → 用 **ELF 符号介入**：
 * 可执行文件开 ENABLE_EXPORTS（-Wl,--export-dynamic）后自身符号进入动态符号表，
 * librtlsdr.so 对 libusb 的调用全部落到本文件的桩函数上。下层伪造一台
 * VID=0x0bda PID=0x2838 的电视棒与三个 USB 字符串描述符；上层的 rtlsdr_* 公开
 * API、机型表匹配、设备索引遍历、序列号反查、越界错误路径全是交付库的真实代码。
 * 只消费交付物 <rtl-sdr.h> + librtlsdr.so；不用 assert 宏，逐项显式比对 + 计数。
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <libusb.h>
#include <rtl-sdr.h>

#define FAKE_VID 0x0bda
#define FAKE_PID 0x2838
#define FAKE_MANUF "FakeVendor Inc."
#define FAKE_PROD "Fake RTL2832U Dongle"
#define FAKE_SERIAL "FAKESERIAL0001"

static int g_list_calls, g_desc_calls, g_str_calls, g_open_calls; /* 设备侧计数 */
static long g_fake_dev, g_fake_handle; /* 只当句柄用（libusb 结构不完整） */

/* ── 被介入的 libusb 符号：设备枚举 + 字符串读取全部路径 ── */
int libusb_init(libusb_context **ctx)
{
	static long token;
	*ctx = (libusb_context *)&token;
	return 0;
}
void libusb_exit(libusb_context *ctx) { (void)ctx; }
ssize_t libusb_get_device_list(libusb_context *ctx, libusb_device ***list)
{
	static libusb_device *devs[2]; /* NULL 结尾 */
	(void)ctx;
	g_list_calls++;
	devs[0] = (libusb_device *)&g_fake_dev;
	devs[1] = NULL;
	*list = devs;
	return 1;
}
void libusb_free_device_list(libusb_device **list, int unref) { (void)list; (void)unref; }
int libusb_get_device_descriptor(libusb_device *dev, struct libusb_device_descriptor *dd)
{
	(void)dev;
	g_desc_calls++;
	memset(dd, 0, sizeof(*dd));
	dd->idVendor = FAKE_VID;
	dd->idProduct = FAKE_PID;
	dd->iManufacturer = 1;
	dd->iProduct = 2;
	dd->iSerialNumber = 3;
	return 0;
}
int libusb_open(libusb_device *dev, libusb_device_handle **handle)
{
	(void)dev;
	g_open_calls++;
	*handle = (libusb_device_handle *)&g_fake_handle;
	return 0;
}
void libusb_close(libusb_device_handle *handle) { (void)handle; }
libusb_device *libusb_get_device(libusb_device_handle *handle)
{
	(void)handle;
	return (libusb_device *)&g_fake_dev;
}
int libusb_get_string_descriptor_ascii(libusb_device_handle *handle, uint8_t idx,
				       unsigned char *data, int length)
{
	static const char *tab[4] = { NULL, FAKE_MANUF, FAKE_PROD, FAKE_SERIAL };
	int n;
	(void)handle;
	if (idx < 1 || idx > 3 || length < 2)
		return -1;
	n = (int)strlen(tab[idx]);
	if (n > length - 1)
		n = length - 1;
	memcpy(data, tab[idx], (size_t)n);
	data[n] = '\0';
	g_str_calls++;
	return n;
}

static int g_checks, g_fails;
static void ck(int ok, const char *what)
{
	g_checks++;
	if (!ok)
		g_fails++;
	printf("  [%s] %s\n", ok ? "ok" : "FAIL", what);
}

int main(void)
{
	rtlsdr_dev_t *dev = NULL;
	char manuf[256] = { 0 }, prod[256] = { 0 }, serial[256] = { 0 };
	const char *name;
	uint32_t count;
	int r, strs_before;

	printf("消费者用例：设备枚举链路（ELF 符号介入伪造 VID=0x%04x PID=0x%04x）\n",
	       FAKE_VID, FAKE_PID);

	count = rtlsdr_get_device_count();
	ck(count == 1, "rtlsdr_get_device_count() 枚举到 1 台假电视棒");
	printf("       count=%u；设备侧 get_device_list=%d 次，读描述符=%d 次\n",
	       count, g_list_calls, g_desc_calls);

	name = rtlsdr_get_device_name(0);
	ck(name && strstr(name, "RTL2832U") && strstr(name, "OEM"),
	   "rtlsdr_get_device_name(0) 按注入的 VID/PID 命中上游机型表");
	printf("       name=\"%s\"\n", name ? name : "(null)");

	r = rtlsdr_get_device_usb_strings(0, manuf, prod, serial);
	ck(r == 0, "rtlsdr_get_device_usb_strings(0, ...) 返回 0");
	ck(!strcmp(manuf, FAKE_MANUF), "厂商串与设备侧注入逐字节一致");
	ck(!strcmp(prod, FAKE_PROD), "产品串与设备侧注入逐字节一致");
	ck(!strcmp(serial, FAKE_SERIAL), "序列号串与设备侧注入逐字节一致");
	printf("       manuf=\"%s\" product=\"%s\" serial=\"%s\"\n", manuf, prod, serial);
	ck(g_open_calls >= 1, "设备侧确认 libusb_open 被真实调用");

	ck(rtlsdr_get_index_by_serial(FAKE_SERIAL) == 0,
	   "rtlsdr_get_index_by_serial() 反查序列号命中索引 0");
	ck(rtlsdr_get_index_by_serial("NO-SUCH-SERIAL") == -3, "未知序列号反查返回 -3");

	name = rtlsdr_get_device_name(9);
	ck(name && name[0],
	   "越界索引 rtlsdr_get_device_name(9) 回退到最后一个匹配机型名（上游实现）");
	/* 上游此处 `r = libusb_init()` 会覆盖掉默认的 -2，越界时既不报错也不写
	 * 缓冲区 → 用哨兵值验证缓冲区确实没被碰过（设备侧也收不到字符串请求）。 */
	strs_before = g_str_calls;
	strcpy(manuf, "SENTINEL");
	strcpy(prod, "SENTINEL");
	strcpy(serial, "SENTINEL");
	r = rtlsdr_get_device_usb_strings(9, manuf, prod, serial);
	ck(!strcmp(manuf, "SENTINEL") && !strcmp(prod, "SENTINEL")
	   && !strcmp(serial, "SENTINEL") && g_str_calls == strs_before,
	   "越界索引 rtlsdr_get_device_usb_strings(9) 不触碰输出缓冲区（无字符串请求）");
	printf("       越界 usb_strings 返回 %d（上游把 -2 覆盖成了 libusb_init 的 0）\n", r);

	r = rtlsdr_open(&dev, 9);
	ck(r != 0, "rtlsdr_open(&dev, 9) 越界失败（返回非 0）");
	ck(dev == NULL, "越界失败时不交出设备句柄（dev 仍为 NULL）");
	ck(g_desc_calls >= 4, "设备侧确认描述符被反复真实读取（>=4 次）");

	printf("设备侧计数：get_device_list=%d 描述符=%d 字符串描述符=%d open=%d\n",
	       g_list_calls, g_desc_calls, g_str_calls, g_open_calls);
	printf("rtlsdr 消费者用例结果：%d 项检查，%d 项失败\n", g_checks, g_fails);
	return g_fails ? 1 : 0;
}
