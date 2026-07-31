/* libmspack 1.11 —— 真实解压器生命周期验证（非 dlopen 空壳）。
 *
 * 判据（不依赖任何 .cab 样例文件）：
 *   ① mspack_version(MSPACK_VER_LIBRARY) 返回正数版本；
 *   ② 真建出 CAB 解压器（会走内部内存分配与系统接口初始化），再正常销毁；
 *   ③ 对**未知的 mspack 类型**要求返回 0 —— 只验成功路径的话，
 *      一个永远返回非零的桩实现也能蒙混过关。
 */
#include <mspack.h>

#include <stdio.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

int main(void) {
    int v = mspack_version(MSPACK_VER_LIBRARY);
    printf("     libmspack 库版本: %d\n", v);
    CHECK(v > 0, "mspack_version(LIBRARY) > 0");

    struct mscab_decompressor *cab = mspack_create_cab_decompressor(NULL);
    CHECK(cab != NULL, "mspack_create_cab_decompressor() 成功");
    if (cab) {
        mspack_destroy_cab_decompressor(cab);
        printf("[ok] mspack_destroy_cab_decompressor() 未崩溃\n");
    }

    /* 未知类型必须报负值，证明版本查询真在查表而不是永远返回常量。
       上游 system.c 的实现：switch 命中的各 case 返回具体版本，落到末尾 `return -1`。
       （先前我按「返回 0」写，实测是 -1——查了上游实现才确认。） */
    CHECK(mspack_version(9999) < 0, "未知 mspack 类型返回负值（排除常量实现）");

    if (failures) { fprintf(stderr, "\nlibmspack: %d 项断言失败\n", failures); return 1; }
    printf("\nlibmspack 1.11: 全部断言通过\n");
    return 0;
}
