/*
 * test_package smoke test for libdom 0.4.2
 *
 * Exercises the public C API of the library (R34: must actually call the
 * package's API, not just print a string):
 *   1. Core DOM:  dom_implementation_create_document +
 *                 dom_document_create_element + dom_document_create_text_node
 *                 + dom_node_append_child / dom_node_get_first_child
 *   2. XML binding (libxml2): dom_xml_parser_create / parse_chunk /
 *                 completed  --  the exact API libsvgtiny uses to load SVG
 *   3. Hubbub binding: dom_hubbub_parser_create / parse_chunk / completed
 *                 (HTML5 parsing into a DOM document)
 *
 * Exit status is 0 only if every check passes.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <dom/dom.h>
#include <dom/walk.h>
#include <dom/bindings/xml/xmlparser.h>
#include <dom/bindings/hubbub/parser.h>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg) do { \
	checks++; \
	if (!(cond)) { \
		fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__); \
		failures++; \
	} else { \
		printf("PASS: %s\n", msg); \
	} \
} while (0)

/* dom_msg callback (never expected to fire on the happy path) */
static void test_msg(uint32_t severity, void *ctx, const char *msg, ...)
{
	(void) severity;
	(void) ctx;
	(void) msg;
}

/* ------------------------------------------------------------------ */
/* 1. Core DOM construction                                            */
/* ------------------------------------------------------------------ */
static void test_core_dom(void)
{
	dom_document *doc = NULL;
	dom_element *elem = NULL;
	dom_text *text = NULL;
	dom_string *tag = NULL;
	dom_string *txt = NULL;
	dom_node *first = NULL;
	dom_node *appended = NULL;
	dom_node_type type;
	dom_exception err;

	err = dom_implementation_create_document(DOM_IMPLEMENTATION_HTML,
			NULL, NULL, NULL, NULL, NULL, &doc);
	CHECK(err == DOM_NO_ERR && doc != NULL, "core: create document");

	err = dom_string_create_interned((const uint8_t *) "p", 1, &tag);
	CHECK(err == DOM_NO_ERR && tag != NULL, "core: intern string 'p'");

	err = dom_document_create_element(doc, tag, &elem);
	CHECK(err == DOM_NO_ERR && elem != NULL, "core: create element <p>");
	dom_string_unref(tag);

	err = dom_string_create_interned((const uint8_t *) "hello", 5, &txt);
	CHECK(err == DOM_NO_ERR && txt != NULL, "core: intern string 'hello'");
	err = dom_document_create_text_node(doc, txt, &text);
	CHECK(err == DOM_NO_ERR && text != NULL, "core: create text node");
	dom_string_unref(txt);

	err = dom_node_append_child((dom_node *) elem, (dom_node *) text,
			&appended);
	CHECK(err == DOM_NO_ERR && appended != NULL,
			"core: append text child to element");
	if (appended != NULL)
		dom_node_unref(appended);

	err = dom_node_get_first_child((dom_node *) elem, &first);
	CHECK(err == DOM_NO_ERR && first != NULL, "core: get first child");
	dom_node_get_node_type(first, &type);
	CHECK(type == DOM_TEXT_NODE, "core: first child is a text node");

	if (first != NULL)
		dom_node_unref(first);
	dom_node_unref((dom_node *) text);
	dom_node_unref((dom_node *) elem);
	dom_node_unref((dom_node *) doc);
}

/* ------------------------------------------------------------------ */
/* 2. XML binding (libxml2) - the parser libsvgtiny uses               */
/* ------------------------------------------------------------------ */
static void test_xml_binding(void)
{
	dom_xml_parser *parser = NULL;
	dom_document *doc = NULL;
	dom_xml_error err;
	static const char xml[] =
		"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
		"<root><child>Hello</child><child>World</child></root>";

	parser = dom_xml_parser_create("UTF-8", NULL, test_msg, NULL, &doc);
	CHECK(parser != NULL, "xml: create parser");
	CHECK(doc != NULL, "xml: create document");

	err = dom_xml_parser_parse_chunk(parser, (uint8_t *) xml, strlen(xml));
	CHECK(err == DOM_XML_OK, "xml: parse chunk");

	err = dom_xml_parser_completed(parser);
	CHECK(err == DOM_XML_OK, "xml: parse completed");

	dom_xml_parser_destroy(parser);
	if (doc != NULL)
		dom_node_unref((dom_node *) doc);
}

/* ------------------------------------------------------------------ */
/* 3. Hubbub binding (HTML5)                                           */
/* ------------------------------------------------------------------ */
static void test_hubbub_binding(void)
{
	dom_hubbub_parser_params params;
	dom_hubbub_parser *parser = NULL;
	dom_document *doc = NULL;
	dom_hubbub_error err;
	static const char html[] =
		"<html><head><title>Test</title></head><body>"
		"<p>Hello World</p></body></html>";

	memset(&params, 0, sizeof(params));
	params.enc = NULL;
	params.fix_enc = true;
	params.enable_script = false;
	params.msg = test_msg;
	params.script = NULL;
	params.ctx = NULL;
	params.daf = NULL;

	err = dom_hubbub_parser_create(&params, &parser, &doc);
	CHECK(err == DOM_HUBBUB_OK, "hubbub: create parser");
	CHECK(parser != NULL, "hubbub: parser object");
	CHECK(doc != NULL, "hubbub: document object");

	err = dom_hubbub_parser_parse_chunk(parser,
			(const uint8_t *) html, strlen(html));
	CHECK(err == DOM_HUBBUB_OK, "hubbub: parse chunk");

	err = dom_hubbub_parser_completed(parser);
	CHECK(err == DOM_HUBBUB_OK, "hubbub: parse completed");

	dom_hubbub_parser_destroy(parser);
	if (doc != NULL)
		dom_node_unref((dom_node *) doc);
}

int main(void)
{
	printf("libdom 0.4.2 smoke test\n");
	test_core_dom();
	test_xml_binding();
	test_hubbub_binding();

	printf("checks=%d failures=%d\n", checks, failures);
	if (failures != 0)
		return 1;
	printf("ALL DOM SMOKE TESTS PASSED\n");
	return 0;
}
