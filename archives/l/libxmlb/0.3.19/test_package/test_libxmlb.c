/* test_libxmlb.c — consumer test for the libxmlb 0.3.19 conan package.
 *
 * Exercises the public API through the pkg-config interface (dependency
 * 'xmlb'): builds a silo from inline XML, queries it with XPath, exports
 * the silo back to XML, and verifies the version metadata. Exits non-zero
 * on the first failed check.
 */
#include <xmlb.h>
#include <glib.h>
#include <stdio.h>
#include <string.h>

static int g_failed = 0;

#define CHECK(cond, msg)                                     \
	do {                                                 \
		if (cond) {                                  \
			g_print("PASS: %s\n", msg);          \
		} else {                                     \
			g_print("FAIL: %s\n", msg);          \
			g_failed++;                          \
		}                                            \
	} while (0)

static const gchar *test_xml =
	"<components origin=\"conan\">"
	"  <component type=\"desktop\">"
	"    <id>org.example.Test</id>"
	"    <name>Test Component</name>"
	"    <pkgname>test-pkg</pkgname>"
	"    <release version=\"1.2.3\"/>"
	"  </component>"
	"  <component type=\"desktop\">"
	"    <id>org.example.Other</id>"
	"    <name>Other Component</name>"
	"  </component>"
	"</components>";

int
main(void)
{
	g_autoptr(GError) error = NULL;
	g_autoptr(XbBuilder) builder = NULL;
	g_autoptr(XbBuilderSource) source = NULL;
	g_autoptr(XbSilo) silo = NULL;
	g_autoptr(XbNode) node = NULL;
	g_autofree gchar *exported = NULL;

	/* 1. version metadata */
	CHECK(XMLB_MAJOR_VERSION == 0 &&
	      XMLB_MINOR_VERSION == 3 &&
	      XMLB_MICRO_VERSION == 19,
	      "version macros are 0.3.19");
	CHECK(g_strcmp0(xb_version_string(), "0.3.19") == 0,
	      "xb_version_string() returns 0.3.19");
	CHECK(LIBXMLB_CHECK_VERSION(0, 3, 0), "LIBXMLB_CHECK_VERSION(0,3,0)");

	/* 2. compile inline XML into a binary silo */
	builder = xb_builder_new();
	source = xb_builder_source_new();
	if (!xb_builder_source_load_xml(source, test_xml,
					XB_BUILDER_SOURCE_FLAG_NONE, &error)) {
		g_printerr("FAIL: xb_builder_source_load_xml: %s\n",
			   error->message);
		return 1;
	}
	xb_builder_import_source(builder, source);
	silo = xb_builder_compile(builder, XB_BUILDER_COMPILE_FLAG_NONE,
				  NULL, &error);
	if (silo == NULL) {
		g_printerr("FAIL: xb_builder_compile: %s\n", error->message);
		return 1;
	}
	CHECK(XB_IS_SILO(silo), "compiled a silo from inline XML");

	/* 3. XPath query through the silo (root element is part of the path) */
	node = xb_silo_query_first(
		silo, "components/component/id[text()='org.example.Test']", &error);
	if (node == NULL) {
		g_printerr("FAIL: xb_silo_query_first: %s\n", error->message);
		return 1;
	}
	CHECK(g_strcmp0(xb_node_get_text(node), "org.example.Test") == 0,
	      "queried component id with XPath");

	/* 4. relative query from a node */
	{
		const gchar *pkgname;
		pkgname = xb_node_query_text(node, "../pkgname", &error);
		CHECK(pkgname != NULL && g_strcmp0(pkgname, "test-pkg") == 0,
		      "relative XPath ../pkgname resolves");
	}

	/* 5. export the silo back to XML text */
	exported = xb_silo_export(silo, XB_NODE_EXPORT_FLAG_NONE, &error);
	if (exported == NULL) {
		g_printerr("FAIL: xb_silo_export: %s\n", error->message);
		return 1;
	}
	CHECK(strstr(exported, "<components") != NULL &&
	      strstr(exported, "org.example.Other") != NULL,
	      "exported silo contains the original content");

	if (g_failed > 0) {
		g_printerr("%d check(s) failed\n", g_failed);
		return 1;
	}
	g_print("All libxmlb consumer checks passed\n");
	return 0;
}
