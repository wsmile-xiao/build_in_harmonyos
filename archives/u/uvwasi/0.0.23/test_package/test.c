/* test_package/test.c — uvwasi 0.0.23 (R34: 实质调用被测包 API) */
#include <uvwasi.h>
#include <stdio.h>

int main(void) {
    /* 版本字符串检查 */
    const char *ver = UVWASI_VERSION_STRING;
    if (!ver || ver[0] == '\0') {
        fprintf(stderr, "UVWASI_VERSION_STRING is empty\n");
        return 1;
    }
    printf("uvwasi version: %s\n", ver);

    /* 错误码 -> 字符串：验证导出符号表可用 */
    const char *ok = uvwasi_embedder_err_code_to_string(UVWASI_ESUCCESS);
    if (!ok) {
        fprintf(stderr, "uvwasi_embedder_err_code_to_string returned NULL\n");
        return 1;
    }
    printf("UVWASI_ESUCCESS -> \"%s\"\n", ok);

    /* 初始化 options 为默认值（fd_table_size 等应被设置） */
    uvwasi_options_t options;
    uvwasi_options_init(&options);
    if (options.fd_table_size == 0) {
        fprintf(stderr, "uvwasi_options_init did not populate fd_table_size\n");
        return 1;
    }

    /* 初始化 uvwasi 实例（内部创建 libuv 事件循环），随后销毁 */
    uvwasi_t uvwasi;
    uvwasi_errno_t err = uvwasi_init(&uvwasi, &options);
    if (err != UVWASI_ESUCCESS) {
        fprintf(stderr, "uvwasi_init failed: %s\n",
                uvwasi_embedder_err_code_to_string(err));
        return 1;
    }
    printf("uvwasi_init succeeded (libuv loop ready); destroying\n");
    uvwasi_destroy(&uvwasi);

    printf("uvwasi test: all API calls passed\n");
    return 0;
}
