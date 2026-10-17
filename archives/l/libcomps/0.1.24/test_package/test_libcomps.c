/* Installed-package consumer test for libcomps 0.1.24.
 *
 * Links against the packaged libcomps and exercises the public API on a real
 * comps document: XML parsing (comps_parse_*), the document filters
 * (comps_doc_get_groups/categories/envs), per-group package queries by type
 * and by name, serialization back to XML (comps2xml_str) and document union
 * (comps_doc_union).  Every check runs against the installed headers and
 * library, so a stub or a mis-installed artifact cannot pass.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libcomps/comps_doc.h>
#include <libcomps/comps_docgroup.h>
#include <libcomps/comps_obj.h>
#include <libcomps/comps_objlist.h>
#include <libcomps/comps_parse.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        checks++;                                                          \
        if (!(cond)) {                                                     \
            failures++;                                                    \
            fprintf(stderr, "FAIL [%s:%d] %s\n", __FILE__, __LINE__, msg); \
        }                                                                  \
    } while (0)

static const char *COMPS_XML =
    "<?xml version='1.0' encoding='UTF-8'?>\n"
    "<!DOCTYPE comps PUBLIC \"-//Red Hat, Inc.//DTD Comps info//EN\" "
    "\"comps.dtd\">\n"
    "<comps>\n"
    "  <group>\n"
    "    <id>core</id>\n"
    "    <name>Core</name>\n"
    "    <description>Core packages</description>\n"
    "    <default>true</default>\n"
    "    <uservisible>true</uservisible>\n"
    "    <packagelist>\n"
    "      <packagereq type=\"mandatory\">bash</packagereq>\n"
    "      <packagereq type=\"mandatory\">glibc</packagereq>\n"
    "      <packagereq type=\"default\">vim</packagereq>\n"
    "      <packagereq type=\"optional\">emacs</packagereq>\n"
    "    </packagelist>\n"
    "  </group>\n"
    "  <group>\n"
    "    <id>devel</id>\n"
    "    <name>Development</name>\n"
    "    <description>Development tools</description>\n"
    "    <default>false</default>\n"
    "    <uservisible>false</uservisible>\n"
    "    <packagelist>\n"
    "      <packagereq type=\"mandatory\">gcc</packagereq>\n"
    "      <packagereq type=\"optional\">gdb</packagereq>\n"
    "    </packagelist>\n"
    "  </group>\n"
    "  <category>\n"
    "    <id>development</id>\n"
    "    <name>Development</name>\n"
    "    <display_order>2</display_order>\n"
    "    <grouplist>\n"
    "      <groupid>devel</groupid>\n"
    "    </grouplist>\n"
    "  </category>\n"
    "  <environment>\n"
    "    <id>minimal</id>\n"
    "    <name>Minimal</name>\n"
    "    <grouplist>\n"
    "      <groupid>core</groupid>\n"
    "    </grouplist>\n"
    "  </environment>\n"
    "</comps>\n";

static const char *COMPS_XML_EXTRA =
    "<comps>\n"
    "  <group>\n"
    "    <id>extras</id>\n"
    "    <name>Extras</name>\n"
    "    <description>Extra packages</description>\n"
    "    <default>false</default>\n"
    "    <uservisible>true</uservisible>\n"
    "    <packagelist>\n"
    "      <packagereq type=\"default\">curl</packagereq>\n"
    "    </packagelist>\n"
    "  </group>\n"
    "</comps>\n";

/* Parse a document through the public parser objects; *parsed_out owns the
 * returned COMPS_Doc.  comps_parse_str() reports -1 for a fatal parse error,
 * 1 for non-fatal diagnostics and 0 when the document was clean, so the return
 * code is handed back to the caller instead of being treated as a boolean. */
static COMPS_Doc *parse_comps(const char *xml, COMPS_Parsed **parsed_out,
                              int *parse_rc)
{
    COMPS_Parsed *parsed = comps_parse_parsed_create();
    int rc;

    if (parse_rc != NULL) {
        *parse_rc = -1;
    }
    if (parsed == NULL) {
        return NULL;
    }
    if (!comps_parse_parsed_init(parsed, "UTF-8", 0)) {
        comps_parse_parsed_destroy(parsed);
        return NULL;
    }
    rc = comps_parse_str(parsed, (char *)xml, NULL);
    if (parse_rc != NULL) {
        *parse_rc = rc;
    }
    if (parsed->comps_doc == NULL) {
        comps_parse_parsed_destroy(parsed);
        return NULL;
    }
    *parsed_out = parsed;
    return parsed->comps_doc;
}

static int str_prop_is(COMPS_Object *value, const char *expected)
{
    int equal = 0;
    char *text;

    if (value == NULL) {
        return 0;
    }
    text = comps_object_tostr(value);
    if (text != NULL) {
        equal = strcmp(text, expected) == 0;
        free(text);
    }
    return equal;
}

static void test_document_structure(void)
{
    COMPS_Parsed *parsed = NULL;
    int parse_rc = -1;
    COMPS_Doc *doc = parse_comps(COMPS_XML, &parsed, &parse_rc);
    COMPS_ObjList *groups;
    COMPS_ObjList *categories;
    COMPS_ObjList *envs;
    COMPS_ObjList *pkgs;
    COMPS_Object *value;
    COMPS_DocGroup *group;

    CHECK(parse_rc >= 0, "comps_parse_str reported a fatal parse error");
    CHECK(doc != NULL, "comps_parse_str did not produce a document");
    if (doc == NULL) {
        return;
    }

    groups = comps_doc_get_groups(doc, NULL, NULL, NULL, NULL, 0);
    categories = comps_doc_get_categories(doc, NULL, NULL, NULL, NULL, 0);
    envs = comps_doc_get_envs(doc, NULL, NULL, NULL, NULL, 0);

    CHECK(groups != NULL && groups->len == 2, "expected 2 groups");
    CHECK(categories != NULL && categories->len == 1, "expected 1 category");
    CHECK(envs != NULL && envs->len == 1, "expected 1 environment");

    group = (COMPS_DocGroup *)comps_objlist_get(groups, 0);
    CHECK(group != NULL, "first group is missing");
    if (group != NULL) {
        value = comps_docgroup_get_id(group);
        CHECK(str_prop_is(value, "core"), "first group id is not 'core'");
        comps_object_destroy(value);

        value = comps_docgroup_get_name(group);
        CHECK(str_prop_is(value, "Core"), "first group name is not 'Core'");
        comps_object_destroy(value);

        value = comps_docgroup_get_uservisible(group);
        CHECK(value != NULL && ((COMPS_Num *)value)->val == 1,
              "first group should be user visible");
        comps_object_destroy(value);

        value = comps_docgroup_get_def(group);
        CHECK(value != NULL && ((COMPS_Num *)value)->val == 1,
              "first group should be a default group");
        comps_object_destroy(value);

        pkgs = comps_docgroup_get_packages(group, NULL, COMPS_PACKAGE_MANDATORY);
        CHECK(pkgs != NULL && pkgs->len == 2,
              "expected 2 mandatory packages in 'core'");
        comps_object_destroy((COMPS_Object *)pkgs);

        pkgs = comps_docgroup_get_packages(group, NULL, COMPS_PACKAGE_DEFAULT);
        CHECK(pkgs != NULL && pkgs->len == 1,
              "expected 1 default package in 'core'");
        comps_object_destroy((COMPS_Object *)pkgs);

        pkgs = comps_docgroup_get_packages(group, NULL, COMPS_PACKAGE_OPTIONAL);
        CHECK(pkgs != NULL && pkgs->len == 1,
              "expected 1 optional package in 'core'");
        comps_object_destroy((COMPS_Object *)pkgs);

        pkgs = comps_docgroup_get_packages(group, "glibc", COMPS_PACKAGE_UNKNOWN);
        CHECK(pkgs != NULL && pkgs->len == 1,
              "the name filter should match 'glibc'");
        comps_object_destroy((COMPS_Object *)pkgs);

        pkgs = comps_docgroup_get_packages(group, "no-such-pkg",
                                          COMPS_PACKAGE_UNKNOWN);
        CHECK(pkgs != NULL && pkgs->len == 0,
              "the name filter should reject an unknown package");
        comps_object_destroy((COMPS_Object *)pkgs);

        pkgs = comps_docgroup_get_packages(group, NULL, COMPS_PACKAGE_UNKNOWN);
        CHECK(pkgs != NULL && pkgs->len == 4, "expected 4 packages in 'core'");
        comps_object_destroy((COMPS_Object *)pkgs);
    }

    group = (COMPS_DocGroup *)comps_objlist_get(groups, 1);
    CHECK(group != NULL, "second group is missing");
    if (group != NULL) {
        value = comps_docgroup_get_id(group);
        CHECK(str_prop_is(value, "devel"), "second group id is not 'devel'");
        comps_object_destroy(value);

        value = comps_docgroup_get_uservisible(group);
        CHECK(value != NULL && ((COMPS_Num *)value)->val == 0,
              "second group should not be user visible");
        comps_object_destroy(value);
    }

    comps_object_destroy((COMPS_Object *)groups);
    comps_object_destroy((COMPS_Object *)categories);
    comps_object_destroy((COMPS_Object *)envs);
    comps_parse_parsed_destroy(parsed);
}

static void test_serialization_roundtrip(void)
{
    COMPS_Parsed *parsed = NULL;
    COMPS_Parsed *reparsed = NULL;
    COMPS_Doc *doc = parse_comps(COMPS_XML, &parsed, NULL);
    COMPS_Doc *doc2;
    COMPS_ObjList *groups;
    COMPS_Object *value;
    char *xml;

    CHECK(doc != NULL, "round-trip: the initial parse failed");
    if (doc == NULL) {
        return;
    }

    xml = comps2xml_str(doc, NULL, NULL);
    CHECK(xml != NULL, "comps2xml_str returned NULL");
    if (xml != NULL) {
        CHECK(strstr(xml, "<id>core</id>") != NULL,
              "the serialized document lost the 'core' group id");
        CHECK(strstr(xml, "mandatory") != NULL,
              "the serialized document lost the package types");

        doc2 = parse_comps(xml, &reparsed, NULL);
        CHECK(doc2 != NULL, "re-parsing the serialized document failed");
        if (doc2 != NULL) {
            groups = comps_doc_get_groups(doc2, NULL, NULL, NULL, NULL, 0);
            CHECK(groups != NULL && groups->len == 2,
                  "the round-trip changed the number of groups");
            if (groups != NULL && groups->len == 2) {
                value = comps_docgroup_get_id(
                    (COMPS_DocGroup *)comps_objlist_get(groups, 0));
                CHECK(str_prop_is(value, "core"),
                      "the round-trip changed the first group id");
                comps_object_destroy(value);
            }
            comps_object_destroy((COMPS_Object *)groups);
            comps_parse_parsed_destroy(reparsed);
        }
        free(xml);
    }

    comps_parse_parsed_destroy(parsed);
}

static void test_union(void)
{
    COMPS_Parsed *parsed_a = NULL;
    COMPS_Parsed *parsed_b = NULL;
    COMPS_Doc *a = parse_comps(COMPS_XML, &parsed_a, NULL);
    COMPS_Doc *b = parse_comps(COMPS_XML_EXTRA, &parsed_b, NULL);
    COMPS_Doc *merged;
    COMPS_ObjList *groups;

    CHECK(a != NULL && b != NULL, "union: parsing the inputs failed");
    if (a == NULL || b == NULL) {
        return;
    }

    merged = comps_doc_union(a, b);
    CHECK(merged != NULL, "comps_doc_union returned NULL");
    if (merged != NULL) {
        groups = comps_doc_get_groups(merged, NULL, NULL, NULL, NULL, 0);
        CHECK(groups != NULL && groups->len == 3,
              "the union of 2 + 1 groups should have 3 groups");
        comps_object_destroy((COMPS_Object *)groups);

        groups = comps_doc_get_groups(merged, "extras", NULL, NULL, NULL, 0);
        CHECK(groups != NULL && groups->len == 1,
              "the 'extras' group is missing from the union");
        comps_object_destroy((COMPS_Object *)groups);

        comps_doc_destroy(merged);
    }

    comps_parse_parsed_destroy(parsed_a);
    comps_parse_parsed_destroy(parsed_b);
}

int main(void)
{
    test_document_structure();
    test_serialization_roundtrip();
    test_union();

    printf("libcomps consumer test: %d checks, %d failures\n", checks, failures);
    if (failures != 0) {
        fprintf(stderr, "libcomps consumer test FAILED\n");
        return 1;
    }
    printf("libcomps consumer test PASSED\n");
    return 0;
}
