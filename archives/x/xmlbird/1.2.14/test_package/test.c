#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <glib.h>
#include <xmlbird.h>

/* xmlbird 功能测试（R34：实质调用被测包 API，非空壳）
 *
 * 验证三个核心能力：
 *  1. BXmlParser 解析并校验合法/非法 XML（b_xml_parser_new + validate）
 *  2. 遍历解析结果，读取根标签名与属性（get_root_tag + b_tag_get_name/
 *     get_attributes + b_attribute_get_name/get_content）
 *  3. XML 实体编码/解码往返（b_xml_parser_encode/decode）
 *
 * 注：OHOS 上 glib/gobject 运行时进程退出清理会触发 SIGTRAP（平台限制，
 * 见 notes.md），故用 _exit() 明确结束进程，绕过退出清理路径。
 */

static int failures = 0;

#define CHECK(cond, msg)                                          \
    do {                                                          \
        if (!(cond)) {                                            \
            fprintf(stderr, "FAIL: %s\n", msg);                   \
            failures++;                                           \
        } else {                                                  \
            printf("PASS: %s\n", msg);                            \
        }                                                         \
    } while (0)

int main(void) {
    /* 1. 解析 + 校验：合法 XML */
    const gchar *valid_xml =
        "<root><child attr=\"value\">text</child></root>";
    BXmlParser *parser = b_xml_parser_new(valid_xml);
    CHECK(parser != NULL, "parser construction (valid xml)");
    CHECK(b_xml_parser_validate(parser) == TRUE, "validate valid xml");

    BTag *root = b_xml_parser_get_root_tag(parser);
    CHECK(root != NULL, "get root tag");
    if (root != NULL) {
        gchar *name = b_tag_get_name(root);
        CHECK(name != NULL && strcmp(name, "root") == 0,
              "root tag name is 'root'");
        g_free(name);
    }

    /* 2. 遍历子标签 */
    BTagIterator *iter = b_tag_iterator(root);
    CHECK(iter != NULL, "tag iterator created");
    gboolean found_child = FALSE;
    if (iter != NULL) {
        while (b_tag_iterator_next(iter)) {
            BTag *child = b_tag_iterator_get(iter);
            gchar *cname = b_tag_get_name(child);
            if (cname != NULL && strcmp(cname, "child") == 0) {
                found_child = TRUE;
                /* 读取属性 */
                BAttributes *attrs = b_tag_get_attributes(child);
                if (attrs != NULL) {
                    BAttributesIterator *ait = b_attributes_iterator(attrs);
                    while (ait != NULL && b_attributes_iterator_next(ait)) {
                        BAttribute *attr = b_attributes_iterator_get(ait);
                        gchar *aname = b_attribute_get_name(attr);
                        gchar *acontent = b_attribute_get_content(attr);
                        if (aname != NULL && strcmp(aname, "attr") == 0 &&
                            acontent != NULL && strcmp(acontent, "value") == 0) {
                            printf("PASS: attribute attr=value found\n");
                        } else {
                            fprintf(stderr, "FAIL: attribute mismatch\n");
                            failures++;
                        }
                        g_free(aname);
                        g_free(acontent);
                    }
                }
            }
            g_free(cname);
        }
        CHECK(found_child, "child tag found via iterator");
    }
    g_object_unref(parser);

    /* 2b. 非法 XML 校验必须失败 */
    BXmlParser *bad = b_xml_parser_new("<root><unclosed></root>");
    CHECK(bad != NULL, "parser construction (invalid xml)");
    CHECK(b_xml_parser_validate(bad) == FALSE, "validate rejects malformed xml");
    g_object_unref(bad);

    /* 3. XML 实体编码/解码往返 */
    const gchar *raw = "\"'<>&";
    gchar *enc = b_xml_parser_encode(raw);
    CHECK(enc != NULL, "encode returns string");
    if (enc != NULL) {
        gchar *dec = b_xml_parser_decode(enc);
        CHECK(dec != NULL && strcmp(dec, raw) == 0,
              "decode(encode(s)) == s roundtrip");
        printf("      encoded: %s\n", enc);
        g_free(dec);
        g_free(enc);
    }

    if (failures == 0) {
        printf("ALL xmlbird tests passed\n");
        fflush(stdout);
        _exit(0);
    }
    fprintf(stderr, "%d xmlbird test(s) FAILED\n", failures);
    fflush(stderr);
    _exit(1);
}
