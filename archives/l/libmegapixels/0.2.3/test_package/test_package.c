#include <libmegapixels.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>

int main(void) {
    char configfile[256];
    memset(configfile, 0, sizeof(configfile));

    // 调用 API，验证返回值在合理范围内（0 成功，-1 未找到）
    int ret = libmegapixels_find_config(sizeof(configfile), configfile);

    printf("libmegapixels_find_config returned: %d\n", ret);

    // 断言：返回值只能是 0（找到）或 -1（未找到），不能是其他值
    assert(ret == 0 || ret == -1);

    if (ret == 0) {
        // 如果找到配置文件，验证路径非空
        assert(strlen(configfile) > 0);
        printf("Found config file: %s\n", configfile);
    } else {
        printf("No config file found (expected in CI environment)\n");
    }

    printf("libmegapixels consumer test: PASSED\n");
    return 0;
}
