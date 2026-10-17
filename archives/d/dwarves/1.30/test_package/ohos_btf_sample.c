/* 鸿蒙专项测试样例源：生成带 BTF 的 ELF 对象供 pahole -F btf 解析。
 * 验证 dwarves 的 BTF 读取/类型打印链路在 OHOS aarch64 上真实可用。 */
#include <stdint.h>

struct ohos_pc_device {
	uint32_t vendor_id;
	uint32_t product_id;
	char name[32];
};

struct ohos_pc_device g_device = { 0x1234, 0xabcd, "ohos-pc" };

int ohos_pc_probe(struct ohos_pc_device *dev)
{
	return dev->vendor_id == 0x1234;
}
