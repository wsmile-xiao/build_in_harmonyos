/* oil_consumer.c — liboil 0.3.17 test_package consumer (HarmonyOS PC / AArch64)
 *
 * 真实调用安装后的 liboil API 做确定性计算，逐项断言数值结果。
 * 无 stub / 无 skip：任何一项不符即非零退出。
 *
 * API 形态（安装头 liboilfuncs.h）: oil_* 为 trampoline 宏，指向
 * oil_function_class_ptr_*；类签名带 stride 参数（字节单位）。
 * 调用前必须 oil_init()。
 *
 * 上游安装布局: include/liboil-0.3/liboil/*.h、-loil-0.3，
 * 与 liboil-0.3.pc 一致。
 */

#include <stdio.h>
#include <string.h>

/* 上游把 OilFunctionClass 完整定义与 oil_class_get() 放在
 * OIL_ENABLE_UNSTABLE_API 守卫内，且库自身与官方消费者（GStreamer 等）
 * 都以 -DOIL_ENABLE_UNSTABLE_API 编译（configure.ac:247）。 */
#define OIL_ENABLE_UNSTABLE_API 1

#include <liboil/liboil.h>
#include <liboil/liboilfuncs.h>
#include <liboil/liboilfunction.h>

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s\n", msg); \
        return 1; \
    } \
    printf("ok: %s\n", msg); \
} while (0)

int main(void)
{
    int i;

    oil_init();

    /* 1) oil_splat_u32(dest, dstr, s1_1, n): 固定值填充 u32 数组 */
    {
        uint32_t dst[8];
        uint32_t val = 0x12345678U;
        for (i = 0; i < 8; i++) dst[i] = 0xDEADBEEFU;
        oil_splat_u32(dst, sizeof(uint32_t), &val, 8);
        for (i = 0; i < 8; i++) {
            if (dst[i] != 0x12345678U) {
                fprintf(stderr, "FAIL: splat_u32[%d]=0x%x\n", i, dst[i]);
                return 1;
            }
        }
        printf("ok: oil_splat_u32 fills 8 elements with 0x12345678\n");
    }

    /* 2) oil_copy_u8(dest, src, n): 字节拷贝 */
    {
        uint8_t src[16], dst[16];
        for (i = 0; i < 16; i++) src[i] = (uint8_t)(i * 7 + 3);
        memset(dst, 0, sizeof(dst));
        oil_copy_u8(dst, src, 16);
        if (memcmp(dst, src, 16) != 0) {
            fprintf(stderr, "FAIL: copy_u8 mismatch\n");
            return 1;
        }
        printf("ok: oil_copy_u8 copies 16 bytes identically\n");
    }

    /* 3) oil_sum_f64(d_1, s, sstr, n): 浮点求和精确比对 */
    {
        double src[5] = {0.5, 1.25, -0.25, 2.0, 0.5};
        double sum = -1.0;
        double expect = 0.5 + 1.25 - 0.25 + 2.0 + 0.5;  /* = 4.0 */
        oil_sum_f64(&sum, src, sizeof(double), 5);
        if (sum != expect) {
            fprintf(stderr, "FAIL: sum_f64 = %.17g, expect %.17g\n",
                    sum, expect);
            return 1;
        }
        printf("ok: oil_sum_f64 = %.1f (exact match)\n", sum);
    }

    /* 4) oil_abs_f32_f32(dest, dstr, src, sstr, n): 负数取绝对值 */
    {
        float src[4] = {-1.5f, 2.5f, -0.25f, 0.0f};
        float dst[4] = {0, 0, 0, 0};
        float expect[4] = {1.5f, 2.5f, 0.25f, 0.0f};
        oil_abs_f32_f32(dst, sizeof(float), src, sizeof(float), 4);
        for (i = 0; i < 4; i++) {
            if (dst[i] != expect[i]) {
                fprintf(stderr, "FAIL: abs_f32[%d] = %g, expect %g\n",
                        i, dst[i], expect[i]);
                return 1;
            }
        }
        printf("ok: oil_abs_f32_f32 (4 elements incl. negatives)\n");
    }

    /* 5) oil_md5(i_4, s_16): 单块 MD5 压缩函数，确定性输出核对。
     * 输入块构造与上游 testsuite/md5.c 的 test() 相同（填充到 64 字节）；
     * 期望值由本机 python hashlib 对 "liboil md5 test\n" 计算：
     *   6c86c52e2b9863d8ed7e5f66dd0f0fa5 */
    {
        static const char *expect_hex =
            "6c86c52e2b9863d8ed7e5f66dd0f0fa5";
        const char *msg = "liboil md5 test\n";
        uint32_t state[4];
        uint32_t src[16];
        uint8_t out[16];
        char hex[33];
        int j, len;
        state[0] = 0x67452301;
        state[1] = 0xefcdab89;
        state[2] = 0x98badcfe;
        state[3] = 0x10325476;
        memset(src, 0, 64);
        len = (int)strlen(msg);
        memcpy(src, msg, len);
        ((uint8_t *)src)[len] = 0x80;
        src[14] = (uint32_t)(len << 3);   /* little-endian bit length */
        src[15] = 0;
        oil_md5(state, src);
        memcpy(out, state, 16);
        for (j = 0; j < 16; j++)
            sprintf(hex + 2 * j, "%02x", out[j]);
        hex[32] = 0;
        if (strcmp(hex, expect_hex) != 0) {
            fprintf(stderr, "FAIL: oil_md5 = %s, expect %s\n",
                    hex, expect_hex);
            return 1;
        }
        printf("ok: oil_md5 block digest = %s\n", hex);
    }

    /* 6) API 完整性: 类注册表可查询 + 引用实现已选择 */
    {
        OilFunctionClass *klass = oil_class_get("sum_f64");
        CHECK(klass != NULL, "oil_class_get(\"sum_f64\") returns a class");
        CHECK(klass->first_impl != NULL,
              "sum_f64 has at least one implementation");
        CHECK(klass->reference_impl != NULL,
              "sum_f64 reference implementation registered");
        CHECK(oil_class_get_n_classes() > 0,
              "class registry is populated");
        printf("ok: sum_f64 registered, n_classes=%d (C impl on aarch64)\n",
               oil_class_get_n_classes());
    }

    printf("oil_consumer: ALL CHECKS PASSED\n");
    return 0;
}
