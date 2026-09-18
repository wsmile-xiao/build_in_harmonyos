#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <execs.h>

/* libexecs 功能断言：
   1. s2argv 把字符串按空白拆分 argv 数组
   2. execs.h 核心符号可链接（execsp 宏/execs_fork_security 符号）
*/
int main(void) {
    int failures = 0;

    /* s2argv */
    char **argv = s2argv("echo hello world");
    if (!argv || !argv[0] || !argv[1] || !argv[2] || argv[3] != NULL) {
        printf("FAIL s2argv: argv 结构不对\n");
        failures++;
    } else if (strcmp(argv[0], "echo") != 0 ||
               strcmp(argv[1], "hello") != 0 ||
               strcmp(argv[2], "world") != 0) {
        printf("FAIL s2argv: 内容不对 [%s][%s][%s]\n",
               argv[0], argv[1], argv[2]);
        failures++;
    } else {
        printf("ok s2argv: [echo][hello][world]\n");
    }
    s2argv_free(argv);

    /* 核心符号链接断言：
       - execs_fork_security / execs_fork_security_arg：libexecs 导出的真实符号
         （execs.c 定义），取地址引用确保链接期符号存在（符号缺失 → 链接失败）。
       - execsp：execs.h 提供的宏（非符号，展开为 _execs_common 调用），
         用 #ifdef 检查头文件接口可用性。 */
    extern int (*execs_fork_security)(void *execs_fork_security_arg);
    extern void *execs_fork_security_arg;
    printf("ok execs_fork_security=%p execs_fork_security_arg=%p 符号可链接\n",
           (void *)&execs_fork_security, &execs_fork_security_arg);
#ifndef execsp
    printf("FAIL execsp 宏缺失\n");
    failures++;
#else
    printf("ok execsp 宏可用\n");
#endif

    if (failures == 0) {
        printf("PASS: libexecs consumer 全部断言通过\n");
        return 0;
    }
    printf("FAIL: %d 项断言失败\n", failures);
    return 1;
}
