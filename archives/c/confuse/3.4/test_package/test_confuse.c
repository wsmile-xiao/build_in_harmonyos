// confuse 3.4 consumer test: exercise real public config-parsing API with assertions.
#include <confuse.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond)                                                        \
    do {                                                                   \
        if (!(cond)) {                                                     \
            printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);    \
            ++failures;                                                    \
        }                                                                  \
    } while (0)

int main(void)
{
    cfg_opt_t opts[] = {
        CFG_STR("name", "nobody", CFGF_NONE),
        CFG_INT("port", 0, CFGF_NONE),
        CFG_BOOL("verbose", cfg_false, CFGF_NONE),
        CFG_FLOAT("ratio", 0.0, CFGF_NONE),
        CFG_STR_LIST("items", 0, CFGF_NONE),
        CFG_END()
    };
    cfg_t *cfg = cfg_init(opts, CFGF_NONE);
    CHECK(cfg != NULL);
    CHECK(cfg_parse(cfg, "test.conf") == CFG_SUCCESS);
    CHECK(strcmp(cfg_getstr(cfg, "name"), "harmonyos") == 0);
    CHECK(cfg_getint(cfg, "port") == 8080);
    CHECK(cfg_getbool(cfg, "verbose") == cfg_true);
    CHECK(cfg_getnfloat(cfg, "ratio", 0) > 2.4 && cfg_getnfloat(cfg, "ratio", 0) < 2.6);
    CHECK(cfg_size(cfg, "items") == 3);
    CHECK(strcmp(cfg_getnstr(cfg, "items", 0), "first") == 0);
    CHECK(strcmp(cfg_getnstr(cfg, "items", 2), "third") == 0);
    /* 默认值路径：未在配置中出现的键回退声明默认 */
    cfg_t *cfg2 = cfg_init(opts, CFGF_NONE);
    CHECK(cfg2 != NULL && strcmp(cfg_getstr(cfg2, "name"), "nobody") == 0);
    cfg_free(cfg);
    cfg_free(cfg2);
    if (failures) {
        printf("confuse consumer test: %d failure(s)\n", failures);
        return 1;
    }
    printf("confuse consumer test OK: cfg_init/parse/str/int/bool/float/list/default\n");
    return 0;
}
