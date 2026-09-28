/* libconfuse 3.3 消费者验证测试 (R34: 必须调用被测包真实 API)
 *
 * 覆盖 cfg_init / cfg_parse_fp / cfg_getstr / cfg_getint / cfg_print 等
 * 核心 API：创建内存配置流，解析后校验取值，再回写验证。
 */
#include <stdio.h>
#include <string.h>

#include <confuse.h>

static int check(int cond, const char *what)
{
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", what);
        return 1;
    }
    return 0;
}

int main(void)
{
    int rc = 0;
    const char *input = "sample {\n"
                        "  option1 = \"hello world\"\n"
                        "  option2 = 42\n"
                        "}\n";
    cfg_opt_t sec_opts[] = {
        CFG_STR("option1", NULL, CFGF_NONE),
        CFG_INT("option2", 0, CFGF_NONE),
        CFG_END()
    };
    cfg_opt_t opts[] = {
        CFG_SEC("sample", sec_opts, CFGF_NONE),
        CFG_END()
    };

    cfg_t *cfg = cfg_init(opts, CFGF_NONE);
    rc |= check(cfg != NULL, "cfg_init");

    FILE *fp = fmemopen((void *)input, strlen(input), "r");
    if (!fp) {
        /* OHOS musl 的 fmemopen 不支持 "r" 模式时回退到 tmpfile 不可写场景，
         * 直接改用 cfg_parse_buf（libconfuse 自身提供的缓冲区解析 API）。 */
        int parse_rc = cfg_parse_buf(cfg, input);
        rc |= check(parse_rc == CFG_SUCCESS, "cfg_parse_buf");
    } else {
        int parse_rc = cfg_parse_fp(cfg, fp);
        fclose(fp);
        rc |= check(parse_rc == CFG_SUCCESS, "cfg_parse_fp");
    }

    cfg_t *sec = cfg_getsec(cfg, "sample");
    rc |= check(sec != NULL, "cfg_getsec");
    if (sec) {
        const char *s = cfg_getstr(sec, "option1");
        int i = cfg_getint(sec, "option2");
        rc |= check(s && strcmp(s, "hello world") == 0, "cfg_getstr(option1)");
        rc |= check(i == 42, "cfg_getint(option2)");
    }

    /* 打印路径验证：写入 stderr（合法 FILE*；tmpfile/fmemopen 受 OHOS 平台限制） */
    int print_rc = cfg_print(cfg, stderr);
    rc |= check(print_rc == 0, "cfg_print");

    cfg_free(cfg);
    printf("libconfuse test: %s\n", rc == 0 ? "PASS" : "FAIL");
    return rc;
}