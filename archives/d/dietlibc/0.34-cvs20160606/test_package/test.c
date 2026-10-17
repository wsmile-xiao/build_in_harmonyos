#include <stdio.h>
#include <string.h>

/* 消费者视角：真实调用 dietlibc API（R34）。
 * dietlibc 的 _start 以 main(argc, argv, envp) 三参数调用入口。 */
int main(int argc, char **argv, char **envp) {
    char buf[64];
    (void)argc;
    (void)argv;
    (void)envp;
    strcpy(buf, "dietlibc");
    strcat(buf, " ok");
    if (strcmp(buf, "dietlibc ok") != 0) {
        return 1;
    }
    if (strlen(buf) != 11) {
        return 2;
    }
    printf("%s\n", buf);
    return 0;
}
