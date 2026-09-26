/*
 * test_appstream.c — Conan test_package L1 消费者验证（R34：必须实质调用被测包 API）
 *
 * 仅通过 appstream 公开头文件（appstream.h）与公开符号，模拟业务上层组件
 * 编译、链接、调用 libappstream 并校验可观察结果；不含库私有头文件。
 */
#include <appstream.h>
#include <glib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const gchar *test_metainfo =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<component type=\"desktop-application\">\n"
    "  <id>org.example.TestPackage.desktop</id>\n"
    "  <name>TestPackage</name>\n"
    "  <summary>test_package consumer check</summary>\n"
    "  <metadata_license>MIT</metadata_license>\n"
    "  <project_license>MIT</project_license>\n"
    "</component>\n";

int
main(void)
{
    g_autoptr(AsMetadata) md = NULL;
    g_autoptr(GError) error = NULL;
    AsComponent *cpt = NULL;
    const gchar *id = NULL;
    int rc = 1;

    md = as_metadata_new ();
    if (md == NULL) {
        fprintf(stderr, "FAIL: as_metadata_new() returned NULL\n");
        return 1;
    }

    if (!as_metadata_parse_data (md, test_metainfo, -1, AS_FORMAT_KIND_XML, &error)) {
        fprintf(stderr, "FAIL: parse: %s\n", error ? error->message : "?");
        goto out;
    }

    cpt = as_metadata_get_component (md);
    if (cpt == NULL) {
        fprintf(stderr, "FAIL: as_metadata_get_component() returned NULL\n");
        goto out;
    }

    id = as_component_get_id (cpt);
    if (id == NULL || strcmp (id, "org.example.TestPackage.desktop") != 0) {
        fprintf(stderr, "FAIL: unexpected component id: %s\n", id ? id : "(null)");
        goto out;
    }

    printf("PASS: appstream consumer: parsed component id=%s\n", id);
    rc = 0;

out:
    if (rc != 0)
        fprintf(stderr, "FAIL: test_appstream consumer check\n");
    return rc;
}
