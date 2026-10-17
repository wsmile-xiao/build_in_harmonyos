/*
 * test_package 消费者验证（R34）：实质调用 libltdl API。
 * 验证 libltdl 头文件 + 库链接正确，且 lt_dlinit/lt_dlopen/lt_dlsym/
 * lt_dlclose/lt_dlexit 在目标平台真实可运行。
 */
#include <ltdl.h>
#include <stdio.h>

int main(void) {
    if (lt_dlinit() != 0) {
        fprintf(stderr, "FAIL: lt_dlinit() failed: %s\n",
                lt_dlerror() ? lt_dlerror() : "(null)");
        return 1;
    }

    /* 主程序伪句柄：dlsym(RTLD_DEFAULT) 语义，必须成功 */
    lt_dlhandle h = lt_dlopen(NULL);
    if (h == NULL) {
        fprintf(stderr, "FAIL: lt_dlopen(NULL) failed: %s\n",
                lt_dlerror() ? lt_dlerror() : "(null)");
        lt_dlexit();
        return 1;
    }

    /* 在 main 程序里查 libc 符号 printf——真实走一遍 lt_dlsym */
    void *sym = lt_dlsym(h, "printf");
    if (sym == NULL) {
        fprintf(stderr, "FAIL: lt_dlsym(handle, printf) failed: %s\n",
                lt_dlerror() ? lt_dlerror() : "(null)");
        lt_dlclose(h);
        lt_dlexit();
        return 1;
    }

    /* 再尝试打开系统 libc 共享库（若平台没有则以 NULL 句柄为准） */
    lt_dlhandle h2 = lt_dlopen("libc.so.6");
    if (h2 != NULL) {
        lt_dlclose(h2);
    }

    lt_dlclose(h);
    if (lt_dlexit() != 0) {
        fprintf(stderr, "FAIL: lt_dlexit() failed\n");
        return 1;
    }
    printf("test libltdl 2.6.0: lt_dlinit/lt_dlopen/lt_dlsym/lt_dlclose/lt_dlexit OK\n");
    return 0;
}
