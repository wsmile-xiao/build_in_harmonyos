/* git-ftp 1.6.0 consumer test
 * 验证 git-ftp 脚本已安装并可执行 --version */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret = system("git-ftp --version > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: git-ftp --version exited with code %d\n", ret);
        return 1;
    }
    printf("git-ftp smoke test PASSED\n");
    return 0;
}
