/* 消费者测试：真实调用 c-ini 公共流式 API（new → feed → seal → 查询 → unref）。
 * 行为断言与上游 test-basic.c 的解析语义一致。
 */
#include <string.h>
#include <c-ini.h>

int main(void) {
    const char *input = "[group]\nkey=value\n";
    CIniReader *reader = NULL;
    CIniDomain *domain = NULL;
    CIniGroup *group;
    CIniEntry *entry;
    int r;

    r = c_ini_reader_new(&reader);
    if (r != 0 || !reader) {
        return 1;
    }

    r = c_ini_reader_feed(reader, (const uint8_t *)input, strlen(input));
    if (r != 0) {
        c_ini_reader_free(reader);
        return 2;
    }

    r = c_ini_reader_seal(reader, &domain);
    c_ini_reader_free(reader);
    if (r != 0 || !domain) {
        return 3;
    }

    group = c_ini_domain_find(domain, "group", 5);
    if (!group) {
        c_ini_domain_unref(domain);
        return 4;
    }

    entry = c_ini_group_find(group, "key", 3);
    if (!entry || strcmp(c_ini_entry_get_value(entry, NULL), "value") != 0) {
        c_ini_domain_unref(domain);
        return 5;
    }

    c_ini_domain_unref(domain);
    return 0;
}
