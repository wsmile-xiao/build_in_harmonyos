/*
 * test_glad.c — glad 2.0.8 L1 消费者测试
 *
 * 真实执行生成 loader 的初始化路径：stub get-proc-address 对
 * glGetString 返回"4.6.0"版本串（驱动 glad_gl_find_core_gl 版本解析），
 * 对 glClear 返回一个真实无害函数（验证函数表填充），其余符号返回
 * NULL，避免初始化期间调用到假地址；无 GPU 上下文也能安全运行。
 */
#include <stdio.h>
#include <string.h>
#include <glad/gl.h>

/* 无害函数：仅作为"已填充"的函数表项地址，测试中不会调用它 */
static void stub_api(void) {}

/* glGetString 的 stub：模拟返回 GL 版本串，驱动 glad 版本解析 */
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

#if !defined(GL_VERSION_4_6) || !defined(GLAD_VERSION_MAJOR) || !defined(GLAD_VERSION_MINOR)
    printf("FAIL: required version macros missing\n");
    return 1;
#endif

    version = gladLoadGL(load);
    if (version == 0) {
        printf("FAIL: gladLoadGL returned 0 with version-string stub\n");
        rc = 1;
    }

    if (GLAD_VERSION_MAJOR(version) != 4) {
        printf("FAIL: version major=%d, expected 4\n", GLAD_VERSION_MAJOR(version));
        rc = 1;
    }

    /* 版本标志应被 glad_gl_find_core_gl 置位 */
    if (GLAD_GL_VERSION_4_6 != 1) {
        printf("FAIL: GLAD_GL_VERSION_4_6 not set after load\n");
        rc = 1;
    }

    /* 函数表应已填充（stub 返回的地址被保存） */
    if (glad_glGetString == NULL) {
        printf("FAIL: glad_glGetString not populated\n");
        rc = 1;
    }
    if (glad_glClear == NULL) {
        printf("FAIL: glad_glClear not populated\n");
        rc = 1;
    }

    if (rc == 0) {
        printf("test_glad OK: loader init executed, version=%d.%d, "
               "function table populated\n",
               GLAD_VERSION_MAJOR(version), GLAD_VERSION_MINOR(version));
    }
    return rc;
}