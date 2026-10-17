/*
 * opengl 4.6 消费者用例 (test_package.c)
 * 仅使用库已安装/导出的公开头文件与公开 API:
 *   <GL/glcorearb.h>      GL_VERSION_4_6 / PFNGLCLEARPROC 等公开宏与函数指针类型
 *   <GL/glext.h>          GL_ARB_* 扩展常量
 *   <GLES2/gl2.h>         GL_ES_VERSION_2_0
 *   <GLES3/gl3.h>         GL_ES_VERSION_3_0
 *   <KHR/khrplatform.h>   khronos_int64_t / khronos_ssize_t 平台类型
 * 编译、链接并运行, 打印可观察断言结果 (返回码非 0 = 失败)。
 */
#include <GL/glcorearb.h>
#include <GL/glext.h>
#include <GLES2/gl2.h>
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
    /* 公开宏 API: OpenGL 4.6 版本标记 (glcorearb.h 中定义为 1) */
#ifdef GL_VERSION_4_6
    CHECK(1, "GL_VERSION_4_6 defined (OpenGL 4.6 core headers)");
#else
    CHECK(0, "GL_VERSION_4_6 defined (OpenGL 4.6 core headers)");
#endif
    CHECK(GL_VERSION_3_0 == 1, "GL_VERSION_3_0 == 1");

    /* 公开调用约定 typedef: 可声明并实例化函数指针 (模拟上层组件注册 GL 回调) */
    PFNGLCLEARPROC clear_fn = 0;
    CHECK(clear_fn == 0, "PFNGLCLEARPROC function-pointer type usable");
    CHECK(sizeof(clear_fn) == sizeof(void (*)(void)), "PFNGLCLEARPROC pointer size == 8");

    /* 扩展常量 (glext.h) */
#ifdef GL_ARB_multisample
    CHECK(1, "GL_ARB_multisample defined (glext.h)");
#else
    CHECK(0, "GL_ARB_multisample defined (glext.h)");
#endif

    /* GLES2 / GLES3 公开宏 */
#ifdef GL_ES_VERSION_2_0
    CHECK(1, "GL_ES_VERSION_2_0 defined (gl2.h)");
#else
    CHECK(0, "GL_ES_VERSION_2_0 defined (gl2.h)");
#endif
#ifdef GL_ES_VERSION_3_0
    CHECK(1, "GL_ES_VERSION_3_0 defined (gl3.h)");
#else
    CHECK(0, "GL_ES_VERSION_3_0 defined (gl3.h)");
#endif

    /* khrplatform 平台类型 (公开 API) */
    khronos_int64_t big = ((khronos_int64_t)1 << 40) + 7;
    CHECK(big == ((khronos_int64_t)1 << 40) + 7, "khronos_int64_t arithmetic works");
    CHECK(sizeof(khronos_ssize_t) == sizeof(void *), "khronos_ssize_t matches pointer size");

    if (g_fail == 0) {
        printf("CONSUMER OVERALL: %d/%d PASSED\n", g_checks, g_checks);
        return 0;
    }
    printf("CONSUMER OVERALL: %d/%d PASSED, %d FAILED\n",
           g_checks - g_fail, g_checks, g_fail);
    return 1;
}
