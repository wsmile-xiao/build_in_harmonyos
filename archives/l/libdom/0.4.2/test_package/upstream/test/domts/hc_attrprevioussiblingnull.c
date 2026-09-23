/*
title: hc_attrPreviousSiblingNull
creator: Curt Arnold
description: 

The "getPreviousSibling()" method for an Attr node should return null.
Retrieve the attribute named "domestic" from the last child of of the
first employee and examine its PreviousSibling node.  This test uses the
"getNamedItem(name)" method from the NamedNodeMap interface.
date: 2002-06-09
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
	dom_nodelist *addressList = NULL;
	dom_node *testNode = NULL;
	dom_namednodemap *attributes = NULL;
	dom_attr *domesticAttr = NULL;
	dom_node *s = NULL;
	const char *test1 = "hc_staff.html";

	doc = load_html(test1, false);	if (doc == NULL) {
		const char *test2 = "hc_staff.xml";

		doc = load_xml(test2, false);
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

	if (addressList != NULL) {
		dom_nodelist_unref(addressList);
		addressList = NULL;
	}
	exp = dom_document_get_elements_by_tag_name((dom_document *)doc, dstring1, &addressList);
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
	exp = dom_nodelist_item((dom_nodelist *)addressList, 0, &testNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (addressList != NULL) { dom_nodelist_unref(addressList); addressList = NULL; }
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
		if (addressList != NULL) { dom_nodelist_unref(addressList); addressList = NULL; }
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
		if (addressList != NULL) { dom_nodelist_unref(addressList); addressList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (domesticAttr != NULL) {
		dom_node_unref(domesticAttr);
		domesticAttr = NULL;
	}
	exp = dom_namednodemap_get_named_item((dom_namednodemap *)attributes, dstring2, &domesticAttr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_namednodemap_get_named_item");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (addressList != NULL) { dom_nodelist_unref(addressList); addressList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (s != NULL) {
		dom_node_unref(s);
		s = NULL;
	}
	exp = dom_node_get_previous_sibling((dom_node *)domesticAttr, &s);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "previousSibling");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (domesticAttr != NULL) { dom_node_unref(domesticAttr); domesticAttr = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
		if (addressList != NULL) { dom_nodelist_unref(addressList); addressList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_null(s));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (s != NULL) { dom_node_unref(s); s = NULL; }
	if (domesticAttr != NULL) { dom_node_unref(domesticAttr); domesticAttr = NULL; }
	if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
	if (testNode != NULL) { dom_node_unref(testNode); testNode = NULL; }
	if (addressList != NULL) { dom_nodelist_unref(addressList); addressList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
