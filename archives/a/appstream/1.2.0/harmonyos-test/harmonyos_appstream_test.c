/*
 * harmonyos_appstream_test.c — HarmonyOS 专项测试 for appstream 1.2.0
 *
 * 通过 libappstream 公开 API（安装头文件 appstream.h / 公开符号）真实解析一段
 * AppStream metainfo XML 并校验解析结果；非空壳测试，不含库私有头文件。
 *
 * 覆盖点（OHOS aarch64）：
 *   1. AsMetadata 公开解析路径 as_metadata_parse_data(AS_FORMAT_KIND_XML)
 *   2. as_metadata_get_component / as_component_get_id / as_component_get_name
 *   3. 编译期版本宏（as-version.h 公开导出）
 *   4. 序列化往返 as_metadata_component_to_metainfo（XML 往返，可观察结果）
 */
#include <appstream.h>
#include <glib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const gchar *test_metainfo =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<component type=\"desktop-application\">\n"
    "  <id>org.example.HarmonyTest.desktop</id>\n"
    "  <name>HarmonyTest</name>\n"
    "  <summary>HarmonyOS appstream smoke test</summary>\n"
    "  <metadata_license>MIT</metadata_license>\n"
    "  <project_license>MIT</project_license>\n"
    "</component>\n";

static int failures = 0;

#define CHECK(cond, msg)                                               \
    do {                                                               \
        if (!(cond)) {                                                 \
            fprintf(stderr, "FAIL: %s (%s:%d)\n", msg, __FILE__, __LINE__); \
            failures++;                                                \
        } else {                                                       \
            printf("ok: %s\n", msg);                                   \
        }                                                              \
    } while (0)

int
main(void)
{
    g_autoptr(AsMetadata) md = NULL;
    g_autoptr(GError) error = NULL;
    AsComponent *cpt = NULL;
    const gchar *id = NULL;
    const gchar *name = NULL;
    g_autofree gchar *xml_out = NULL;

    /* 编译期版本宏（公开头文件导出） */
    CHECK(AS_MAJOR_VERSION == 1 && AS_MINOR_VERSION == 2 && AS_MICRO_VERSION == 0,
          "as-version.h macros report 1.2.0");
    CHECK(AS_CHECK_VERSION(1, 2, 0), "as_version_greater_or_equal(1.2.0)");

    /* 公开 API：解析 metainfo */
    md = as_metadata_new ();
    CHECK(md != NULL, "as_metadata_new() returns object");

    gboolean ok = as_metadata_parse_data (md, test_metainfo, -1,
                                          AS_FORMAT_KIND_XML, &error);
    CHECK(ok, "as_metadata_parse_data(XML) succeeds");
    if (!ok) {
        fprintf(stderr, "  parse error: %s\n", error ? error->message : "?");
        failures++;
        return 1;
    }

    /* 公开 API：读取解析出的组件 */
    cpt = as_metadata_get_component (md);
    CHECK(cpt != NULL, "as_metadata_get_component() returns component");
    if (cpt == NULL) {
        failures++;
        return 1;
    }

    id = as_component_get_id (cpt);
    name = as_component_get_name (cpt);
    CHECK(id != NULL && strcmp (id, "org.example.HarmonyTest.desktop") == 0,
          "as_component_get_id() == org.example.HarmonyTest.desktop");
    CHECK(name != NULL && strcmp (name, "HarmonyTest") == 0,
          "as_component_get_name() == HarmonyTest");
    printf("  id=%s name=%s\n", id ? id : "(null)", name ? name : "(null)");

    /* 公开 API：序列化往返（metainfo XML 往返，验证可观察输出） */
    xml_out = as_metadata_component_to_metainfo (md, AS_FORMAT_KIND_XML, &error);
    CHECK(xml_out != NULL, "as_metadata_component_to_metainfo() succeeds");
    if (xml_out != NULL) {
        CHECK(strstr (xml_out, "org.example.HarmonyTest.desktop") != NULL,
              "serialized XML contains component id");
        CHECK(strstr (xml_out, "<component") != NULL,
              "serialized XML contains component element");
        printf("  serialized: %.120s...\n", xml_out);
    }

    if (failures == 0) {
        printf("\nPASS: appstream HarmonyOS smoke test (all checks ok)\n");
        return 0;
    }
    fprintf(stderr, "\nFAIL: %d check(s) failed\n", failures);
    return 1;
}