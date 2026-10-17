/* libmspack 0.11alpha —— 真实 API 验证（非 dlopen/print 空壳）。
 *
 * 判据（不依赖任何外部 .cab 样例文件）：
 *   ① mspack_version(MSPACK_VER_LIBRARY) 返回正数；
 *   ② 版本表**差异化**查询：LIBRARY(0)→1、MSCABD(2)→2、MSCABC(3)→0，
 *      三处返回值各不相同 —— 单一常量或仅返回非零的桩实现都过不了；
 *   ③ 真建出 CAB 解压器（走内部内存分配与默认 mspack_system 初始化）再正常销毁；
 *   ④ 未知类型返回负值（上游 system.c: switch 落空后 `return -1`）。
 */
#include <mspack.h>

#include <stdio.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (msg), __FILE__, __LINE__); ++failures; } \
    else { printf("[ok] %s\n", (msg)); } \
} while (0)

int main(void) {
    int lib_ver = mspack_version(MSPACK_VER_LIBRARY);
    int cab_ver = mspack_version(MSPACK_VER_MSCABD);
    int cabc_ver = mspack_version(MSPACK_VER_MSCABC);
    printf("     版本表: LIBRARY=%d MSCABD=%d MSCABC=%d\n",
           lib_ver, cab_ver, cabc_ver);

    CHECK(lib_ver > 0, "mspack_version(MSPACK_VER_LIBRARY) > 0");
    CHECK(lib_ver == 1 && cab_ver == 2 && cabc_ver == 0 && lib_ver != cab_ver && cab_ver != cabc_ver,
          "版本表差异化查询正确（LIBRARY=1 / MSCABD=2 / MSCABC=0，排除常量实现）");

    struct mscab_decompressor *cab = mspack_create_cab_decompressor(NULL);
    CHECK(cab != NULL, "mspack_create_cab_decompressor(NULL) 成功");
    if (cab) {
        mspack_destroy_cab_decompressor(cab);
        printf("[ok] mspack_destroy_cab_decompressor() 未崩溃\n");
    }

    CHECK(mspack_version(9999) < 0, "未知 mspack 类型返回负值（上游 switch 落空 return -1）");

    if (failures) {
        fprintf(stderr, "\nlibmspack: %d 项断言失败\n", failures);
        return 1;
    }
    printf("\nlibmspack 0.11alpha: 全部断言通过\n");
    return 0;
}
