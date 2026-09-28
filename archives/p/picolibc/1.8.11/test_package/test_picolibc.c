#include <string.h>
#include <stdlib.h>

/* 消费者视角：真实调用 picolibc API（R34）。
 * picolibc 是 bare-metal libc，_start 以 main(argc, argv, envp) 三参数调用入口，
 * 且 freestanding 环境 main 返回后不调用 exit（见 picocrt/crt0-none.c）。
 * 本测试覆盖字符串/内存/堆管理核心 API，验证「安装后的头文件 + 静态库可正确编译链接」。 */
int main(int argc, char **argv, char **envp)
{
    char buf[64];
    void *p;
    (void)argc;
    (void)argv;
    (void)envp;

    strcpy(buf, "picolibc");
    strcat(buf, " ok");
    if (strcmp(buf, "picolibc ok") != 0)
        return 1;
    if (strlen(buf) != 11)
        return 2;

    p = malloc(64);
    if (!p)
        return 3;
    memcpy(p, buf, 12);
    if (memcmp(p, buf, 12) != 0) {
        free(p);
        return 4;
    }
    free(p);

    return 0;
}
