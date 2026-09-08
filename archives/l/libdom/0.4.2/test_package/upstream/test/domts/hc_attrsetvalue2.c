/*
title: hc_attrsetvalue2
creator: Curt Arnold
description: 

Sets Attr.value on an attribute that should contain multiple child nodes.
date: 2004-01-01
*/

#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>

#include <dom/dom.h>
#include <dom/functypes.h>

#include <domts.h>

dom_implementation  *doc_impl;

int main(int argc, char  **argv)
{
	dom_exception exp;

	(void)argc;
	(void)argv;

	if (chdir("test/testcases/tests/level1/core/files") < 0) {
		perror("chdir (\"test/testcases/tests/level1/core/files)\"");
		return 1;
	}
	int list_temp[100], count = -1;
	dom_document *doc = NULL;
	dom_nodelist *acronymList = NULL;
	dom_node *testNode = NULL;
	dom_namednodemap *attributes = NULL;
	dom_attr *titleAttr = NULL;
	dom_string *value = NULL;
	dom_text *textNode = NULL;
	dom_node *retval = NULL;
	dom_node *firstChild = NULL;
	dom_node *otherChild = NULL;
	const char *test1 = "hc_staff.html";

	doc = load_html(test1, true);	if (doc == NULL) {
		const char *test2 = "hc_staff.xml";

		doc = load_xml(test2, true);
		if (doc == NULL)
			return 1;
		}
	exp = dom_document_get_implementation((dom_document *) doc, &doc_impl);
	if (exp != DOM_NO_ERR)
		return exp;
	const char *string1 = "acronym";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (acronymList != NULL) {
		dom_nodelist_unref(acronymList);
		acronymList = NULL;
	}
	exp = dom_document_get_elements_by_tag_name((dom_document *)doc, dstring1, &acronymList);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_get_elements_by_tag_name");
		dom_string_unref(dstring1);
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (testNode != NULL) {
		dom_node_unref(testNode);
		testNode = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)acronymList, 3, &testNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (attributes != NULL) {
		dom_namednodemap_unref(attributes);
		attributes = NULL;
	}
	exp = dom_node_get_attributes((dom_node *)testNode, &attributes);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "attributes");
		dom_string_unref(dstring1);
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "title";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (titleAttr != NULL) {
		dom_node_unref(titleAttr);
		titleAttr = NULL;
	}
	exp = dom_namednodemap_get_named_item((dom_namednodemap *)attributes, dstring2, &titleAttr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_namednodemap_get_named_item");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string3 = "terday";
	dom_string *dstring3;
	exp = dom_string_create((const uint8_t *)string3,
			strlen(string3), &dstring3);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (textNode != NULL) {
		dom_node_unref(textNode);
		textNode = NULL;
	}
	exp = dom_document_create_text_node((dom_document *)doc, dstring3, &textNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_text_node");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (retval != NULL) {
		dom_node_unref(retval);
		retval = NULL;
	}
	exp = dom_node_append_child((dom_node *)titleAttr, textNode, &retval);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_node_append_child");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (firstChild != NULL) {
		dom_node_unref(firstChild);
		firstChild = NULL;
	}
	exp = dom_node_get_first_child((dom_node *)titleAttr, &firstChild);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "firstChild");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert((false == is_null(firstChild)));
	const char *string4 = "Tomorrow";
	dom_string *dstring4;
	exp = dom_string_create((const uint8_t *)string4,
			strlen(string4), &dstring4);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

exp = dom_attr_set_value(titleAttr, dstring4);		if (exp != DOM_NO_ERR) {
			fprintf(stderr, "Exception raised when fetch attribute %s", "value");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

			return exp;
		}
	const char *string5 = "impl reused node";
	dom_string *dstring5;
	exp = dom_string_create((const uint8_t *)string5,
			strlen(string5), &dstring5);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

exp = dom_node_set_node_value(firstChild, dstring5);		if (exp != DOM_NO_ERR) {
			fprintf(stderr, "Exception raised when fetch attribute %s", "nodeValue");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

			return exp;
		}
	if (value != NULL) {
		dom_string_unref(value);
		value = NULL;
	}
	exp = dom_attr_get_value((dom_attr *)titleAttr, &value);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "value");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("Tomorrow", value, false));
	if (value != NULL) {
		dom_string_unref(value);
		value = NULL;
	}
	exp = dom_node_get_node_value((dom_node *)titleAttr, &value);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeValue");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		if (value != NULL) { dom_string_unref(value); value = NULL; }
		if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("Tomorrow", value, false));
	if (firstChild != NULL) {
		dom_node_unref(firstChild);
		firstChild = NULL;
	}
	exp = dom_node_get_last_child((dom_node *)titleAttr, &firstChild);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "lastChild");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		if (value != NULL) { dom_string_unref(value); value = NULL; }
		if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (value != NULL) {
		dom_string_unref(value);
		value = NULL;
	}
	exp = dom_node_get_node_value((dom_node *)firstChild, &value);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeValue");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		if (value != NULL) { dom_string_unref(value); value = NULL; }
		if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("Tomorrow", value, false));
	if (otherChild != NULL) {
		dom_node_unref(otherChild);
		otherChild = NULL;
	}
	exp = dom_node_get_next_sibling((dom_node *)firstChild, &otherChild);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nextSibling");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		if (value != NULL) { dom_string_unref(value); value = NULL; }
		if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
		if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_null(otherChild));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	dom_string_unref(dstring3);
	dom_string_unref(dstring4);
	dom_string_unref(dstring5);
	if (otherChild != NULL) { dom_node_unref(otherChild); otherChild = NULL; }
	if (value != NULL) { dom_string_unref(value); value = NULL; }
	if (firstChild != NULL) { dom_node_unref(firstChild); firstChild = NULL; }
	if (retval != NULL) { dom_node_unref(retval); retval = NULL; }
	if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
	if (titleAttr != NULL) { dom_node_unref(titleAttr); titleAttr = NULL; }
	if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
	if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
	if (acronymList != NULL) { dom_nodelist_unref(acronymList); acronymList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
