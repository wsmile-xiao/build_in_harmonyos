#include <stdlib.h>
#include <stdio.h>
#include <sys/wait.h>

int main() {
    /* lv 支持 -h（帮助）并返回 0；--help 是未知选项会返回非零，故用 -h */
    int ret = system("lv -h > /dev/null 2>&1");
    /* system() 返回值是 wait status，需用 WEXITSTATUS 解码出子进程退出码 */
    if (ret == -1 || !WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        printf("FAIL: lv -h failed with exit code %d\n", ret);
        return 1;
    }
    printf("test lv 4.51-10.1: OK (lv -h passed)\n");
    return 0;
}
