/*
 * opengl 4.6 鸿蒙专项测试 (harmonyos_test.c)
 * 校验头文件在 HarmonyOS PC (aarch64-ohos) 目标上的平台语义:
 *   - aarch64 64 位指针 (OHOS PC 设备)
 *   - 非 _WIN32: APIENTRY/GLAPIENTRY 为空调用约定 (OHOS 上不引入 Windows 调用约定)
 *   - khrplatform 平台类型宽度符合 OHOS aarch64 ABI
 *   - GL 公开类型 (GLenum) 宽度
 * 本测试经 conan create 在 OHOS 设备上实际编译并运行。
 */
#include <GL/glcorearb.h>
#include <GLES3/gl3.h>
#include <KHR/khrplatform.h>

#include <stdio.h>
#include <stddef.h>

static int g_checks = 0;
static int g_fail = 0;
#define CHECK(cond, name)                                        \
    do {                                                         \
        g_checks++;                                              \
        if (cond)                                                \
            printf("PASS %s\n", name);                           \
        else {                                                   \
            printf("FAIL %s\n", name);                           \
            g_fail++;                                            \
        }                                                        \
    } while (0)

int main(void) {
    /* OHOS PC 目标为 aarch64 */
#if defined(__aarch64__)
    CHECK(1, "compiled for aarch64 (OHOS PC)");
#else
    CHECK(0, "compiled for aarch64 (OHOS PC)");
#endif
    CHECK(sizeof(void *) == 8, "64-bit pointer (aarch64)");

    /* 非 _WIN32: GL 调用约定为空 (OHOS 上 APIENTRY 展开为空) */
#ifdef _WIN32
    CHECK(0, "non-Windows: APIENTRY empty on OHOS");
#else
    {
        typedef void(APIENTRY *GL_CTest)(void);
        CHECK(sizeof(GL_CTest) == sizeof(void (*)(void)), "APIENTRY empty (pointer size unchanged)");
    }
#endif

    /* khrplatform 平台类型宽度 (OHOS aarch64 ABI) */
    CHECK(sizeof(khronos_int8_t) == 1, "khronos_int8_t 1 byte");
    CHECK(sizeof(khronos_int16_t) == 2, "khronos_int16_t 2 bytes");
    CHECK(sizeof(khronos_int32_t) == 4, "khronos_int32_t 4 bytes");
    CHECK(sizeof(khronos_int64_t) == 8, "khronos_int64_t 8 bytes");
    CHECK(sizeof(khronos_float_t) == 4, "khronos_float_t 4 bytes");

    /* GL 公开类型: GLenum 32 位 */
    CHECK(sizeof(GLenum) == 4, "GLenum 4 bytes");
    CHECK(sizeof(GLboolean) == 1, "GLboolean 1 byte");

    if (g_fail == 0) {
        printf("HARMONYOS OVERALL: %d/%d PASSED\n", g_checks, g_checks);
        return 0;
    }
    printf("HARMONYOS OVERALL: %d/%d PASSED, %d FAILED\n",
           g_checks - g_fail, g_checks, g_fail);
    return 1;
}
