/*
 * libextractor 1.13 消费者测试（test_package）
 *
 * 以库使用者身份编译、链接并调用 libextractor 公开 API：
 *   EXTRACTOR_plugin_add_defaults / EXTRACTOR_plugin_add / EXTRACTOR_extract /
 *   EXTRACTOR_plugin_remove_all / EXTRACTOR_metatype_get_max /
 *   EXTRACTOR_metatype_to_string
 * 退出码由提取到的元数据内容决定；被测资产是本文件内嵌的一段 man page 源码，
 * man 插件从中解出 title / modification date / book title。
 */
#include "extractor.h"

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SAMPLE_FILE "qc4_consumer_sample.1"
#define MAX_ITEMS 64

static const char sample_man[] =
    ".TH QC4-CONSUMER 1 \"2026-09-21\" \"libextractor 1.13\" \"Consumer test document\"\n"
    ".SH NAME\n"
    "qc4-consumer \\- man page written by the conan test_package consumer test\n"
    ".SH SYNOPSIS\n"
    ".B qc4-consumer\n"
    ".RI [ options ]\n"
    ".SH DESCRIPTION\n"
    "This document exists so that libextractor can recover its title, its\n"
    "modification date and its source through the public API.\n"
    ".SH AUTHOR\n"
    "Written by QC-4 <qzy@localhost>\n";

struct collected {
    int total;
    char values[MAX_ITEMS][128];
    char types[MAX_ITEMS][64];
};

static int collect(void *cls, const char *plugin_name, enum EXTRACTOR_MetaType type,
                   enum EXTRACTOR_MetaFormat format, const char *data_mime_type,
                   const char *data, size_t data_len) {
    struct collected *c = (struct collected *) cls;

    (void) plugin_name;
    (void) format;
    (void) data_mime_type;
    if (c->total < MAX_ITEMS) {
        snprintf(c->types[c->total], sizeof(c->types[0]), "%s",
                 EXTRACTOR_metatype_to_string(type));
        snprintf(c->values[c->total], sizeof(c->values[0]), "%.*s",
                 (int) data_len, NULL != data ? data : "");
    }
    c->total++;
    return 0;
}

static int has_value(const struct collected *c, const char *want) {
    int i;

    for (i = 0; i < c->total && i < MAX_ITEMS; i++) {
        if (0 == strcmp(c->values[i], want)) {
            return 1;
        }
    }
    return 0;
}

static int has_type_value(const struct collected *c, const char *type, const char *want) {
    int i;

    for (i = 0; i < c->total && i < MAX_ITEMS; i++) {
        if (0 == strcmp(c->types[i], type) && 0 == strcmp(c->values[i], want)) {
            return 1;
        }
    }
    return 0;
}

/* 跑一遍指定执行策略的完整提取并核对断言；返回 0 表示该策略下全部成立 */
static int run_policy(const char *policy, enum EXTRACTOR_Options opt) {
    struct collected c;
    struct EXTRACTOR_PluginList *plugins;
    int i;

    memset(&c, 0, sizeof(c));
    plugins = EXTRACTOR_plugin_add_defaults(opt);
    if (NULL == plugins) {
        printf("FAIL[%s]: EXTRACTOR_plugin_add_defaults() returned NULL "
               "(插件目录不可用？检查 LIBEXTRACTOR_PREFIX)\n", policy);
        return 1;
    }
    EXTRACTOR_extract(plugins, SAMPLE_FILE, NULL, 0, &collect, &c);
    EXTRACTOR_plugin_remove_all(plugins);

    printf("[%s] %d item(s)\n", policy, c.total);
    for (i = 0; i < c.total && i < MAX_ITEMS; i++) {
        printf("  %-24s = %s\n", c.types[i], c.values[i]);
    }
    if (c.total < 5) {
        printf("FAIL[%s]: expected >= 5 metadata items, got %d\n", policy, c.total);
        return 1;
    }
    if (!has_type_value(&c, "title", "QC4-CONSUMER")) {
        printf("FAIL[%s]: title 'QC4-CONSUMER' not extracted\n", policy);
        return 1;
    }
    if (!has_value(&c, "2026-09-21")) {
        printf("FAIL[%s]: modification date '2026-09-21' not extracted\n", policy);
        return 1;
    }
    if (!has_value(&c, "Consumer test document")) {
        printf("FAIL[%s]: manual header not extracted\n", policy);
        return 1;
    }
    return 0;
}

int main(void) {
    struct EXTRACTOR_PluginList *single;
    FILE *fh;
    int failed = 0;

    /* 默认策略下插件跑在子进程里，子进程退出后向管道写入得到 EPIPE 属正常
     * 控制流，上游 tests 同样显式忽略 SIGPIPE。 */
    signal(SIGPIPE, SIG_IGN);

    fh = fopen(SAMPLE_FILE, "wb");
    if (NULL == fh) {
        perror("fopen(" SAMPLE_FILE ")");
        return 1;
    }
    fwrite(sample_man, 1, sizeof(sample_man) - 1, fh);
    if (0 != fclose(fh)) {
        printf("FAIL: cannot write test document\n");
        return 1;
    }

    if (EXTRACTOR_metatype_get_max() <= 0) {
        printf("FAIL: EXTRACTOR_metatype_get_max() returned %d\n",
               (int) EXTRACTOR_metatype_get_max());
        failed = 1;
    }
    if (0 != strcmp(EXTRACTOR_metatype_to_string(EXTRACTOR_METATYPE_TITLE), "title")) {
        printf("FAIL: metatype name for TITLE is '%s'\n",
               EXTRACTOR_metatype_to_string(EXTRACTOR_METATYPE_TITLE));
        failed = 1;
    }
    single = EXTRACTOR_plugin_add(NULL, "man", NULL, EXTRACTOR_OPTION_DEFAULT_POLICY);
    if (NULL == single) {
        printf("FAIL: cannot load the single 'man' plugin by name\n");
        failed = 1;
    } else {
        EXTRACTOR_plugin_remove_all(single);
    }
    /* 两种执行策略都必须解出同样的元数据：默认（插件子进程 + IPC）与 in-process */
    if (0 != run_policy("default-policy", EXTRACTOR_OPTION_DEFAULT_POLICY)) {
        failed = 1;
    }
    if (0 != run_policy("in-process", EXTRACTOR_OPTION_IN_PROCESS)) {
        failed = 1;
    }
    if (0 != failed) {
        printf("test_libextractor: FAILED\n");
        return 1;
    }
    printf("test_libextractor: OK\n");
    return 0;
}
