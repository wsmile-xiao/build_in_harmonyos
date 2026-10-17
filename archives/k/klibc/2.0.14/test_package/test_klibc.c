#include <stdio.h>
#include <string.h>

/* 消费者视角：真实调用 klibc API（R34）。
 * klibc 的 _start 以 main(argc, argv, envp) 三参数调用入口（见 libc_init.c）。 */
int main(int argc, char **argv, char **envp)
{
    char buf[64];
    (void)argc;
    (void)argv;
    (void)envp;
    strcpy(buf, "klibc");
    strcat(buf, " ok");
    if (strcmp(buf, "klibc ok") != 0)
        return 1;
    if (strlen(buf) != 8)
        return 2;
    printf("%s\n", buf);
    return 0;
}
