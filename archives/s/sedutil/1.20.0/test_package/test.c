#include <stdio.h>
#include <stdlib.h>

/* 参考消费者测试：实质调用被测包二进制 sedutil-cli --scan 并检查返回码。
 * 主要测试路径由 test_package/conanfile.py 的 test()（VirtualRunEnv 直接运行
 * sedutil-cli --scan）执行；本文件同时满足 L0c 测试源文件门禁，可独立编译验证。 */
int main(void) {
    int rc = system("sedutil-cli --scan >/dev/null 2>&1");
    printf("test sedutil 1.20.0: sedutil-cli --scan rc=%d\n", rc);
    return rc == 0 ? 0 : 1;
}
