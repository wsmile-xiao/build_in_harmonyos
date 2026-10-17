/* consumer_zpl.c — 独立消费者验证用例（模拟业务上层组件）。
 *
 * 仅通过 zpl 已安装/导出的公开头文件 <zpl.h> 与公开 API 使用该库：
 * 不包含库私有头、不调用内部符号、不复用库内部测试构建目录。
 * 业务场景：上层应用将一行用户输入做 base64 编码后存储，再用
 * zpl 的 hash 计算键值，最后从解码结果恢复原串并校验。
 *
 * 编译（仅公开头，未链接任何 zpl 编译产物——单头库无链接目标）：
 *   clang -I<prefix>/include -std=gnu99 -O1 -o consumer_zpl consumer_zpl.c
 */
#define ZPL_IMPLEMENTATION
#include <zpl.h>

int main(void)
{
    char const *user_input = "user=alice&action=login&token=zpl-consumer";
    int failures = 0;

    /* 1. 公开 API：base64 编码（存储侧） */
    zpl_u8 *stored = zpl_base64_encode(zpl_heap(), user_input, zpl_strlen(user_input));
    if (!stored) {
        zpl_printf("consumer FAIL: base64 encode NULL\n");
        return 1;
    }
    zpl_printf("consumer: stored base64 = %s\n", stored);

    /* 2. 公开 API：fnv64a 键值计算 */
    zpl_u64 key = zpl_fnv64a(user_input, zpl_strlen(user_input));
    zpl_printf("consumer: fnv64a key = 0x%016llx\n", (unsigned long long)key);
    if (key == 0) failures++;

    /* 3. 公开 API：base64 解码恢复（读取侧）并校验与原始输入一致 */
    zpl_u8 *restored = zpl_base64_decode(zpl_heap(), stored, zpl_strlen(stored));
    if (!restored) {
        zpl_printf("consumer FAIL: base64 decode NULL\n");
        return 1;
    }
    if (zpl_strcmp(user_input, restored) != 0) {
        zpl_printf("consumer FAIL: round-trip mismatch\n");
        failures++;
    } else {
        zpl_printf("consumer: restored input = %s\n", restored);
    }

    if (failures) {
        zpl_printf("consumer_zpl: %d failure(s)\n", failures);
        return 1;
    }
    zpl_printf("consumer_zpl: ALL OK\n");
    return 0;
}
