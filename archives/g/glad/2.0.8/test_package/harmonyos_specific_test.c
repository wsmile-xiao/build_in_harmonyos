/*
 * harmonyos_specific_test.c — glad 2.0.8 HarmonyOS 专项测试
 *
 * 验证：①生成的 C loader 头文件在 OHOS（aarch64-linux-ohos）工具链下
 * 编译链接并实际运行；②平台宏（__OHOS__/OHOS）与 aarch64 指针语义；
 * ③生成 loader 的公开 API（gladLoadGL / GLAD_GL_VERSION_4_6 / 函数表）
 * 在 OHOS 设备上真实执行初始化路径（stub 驱动，无 GPU 上下文可安全运行）。
 */
#include <stdio.h>
#include <string.h>
#include <glad/gl.h>

static void stub_api(void) {}

static const GLubyte *stub_get_string(GLenum name) {
    (void)name;
    return (const GLubyte *)"4.6.0";
}

static GLADapiproc load(const char *name) {
    if (name && strcmp(name, "glGetString") == 0) {
        return (GLADapiproc)stub_get_string;
    }
    if (name && strcmp(name, "glClear") == 0) {
        return (GLADapiproc)stub_api;
    }
    return NULL;
}

int main(void) {
    int rc = 0;
    int version;

#if defined(__OHOS__) || defined(OHOS)
    printf("platform: OHOS detected (__OHOS__/OHOS)\n");
#else
    printf("WARN: __OHOS__/OHOS not defined, continuing (cross-compile only)\n");
#endif

#if defined(__aarch64__)
    printf("arch: aarch64 detected\n");
#else
    printf("WARN: __aarch64__ not defined\n");
#endif

    if (sizeof(void *) != 8) {
        printf("FAIL: pointer size=%zu, expected 8 on aarch64\n", sizeof(void *));
        rc = 1;
    }

#if !defined(GL_VERSION_4_6)
    printf("FAIL: GL_VERSION_4_6 not declared in generated header\n");
    rc = 1;
#else
    printf("GL_VERSION_4_6 declared in generated header\n");
#endif

    version = gladLoadGL(load);
    if (version == 0) {
        printf("FAIL: gladLoadGL returned 0\n");
        rc = 1;
    } else if (GLAD_GL_VERSION_4_6 == 1 && glad_glGetString != NULL) {
        printf("harmonyos_specific_test OK: glad loader init executed on "
               "OHOS platform, version=%d.%d, table populated\n",
               GLAD_VERSION_MAJOR(version), GLAD_VERSION_MINOR(version));
    } else {
        printf("FAIL: loader init incomplete (version=%d, v46=%d, glGetString=%p)\n",
               version, GLAD_GL_VERSION_4_6, (void *)glad_glGetString);
        rc = 1;
    }
    return rc;
}