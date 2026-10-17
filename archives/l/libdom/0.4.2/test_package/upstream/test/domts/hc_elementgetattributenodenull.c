/*
title: hc_elementGetAttributeNodeNull
creator: Curt Arnold
description: 

    The "getAttributeNode(name)" method retrieves an
   attribute node by name.  It should return null if the
   "strong" attribute does not exist.
   
   Retrieve the last child of the first employee and attempt
   to retrieve a non-existing attribute.  The method should
   return "null".  The non-existing attribute to be used
   is "invalidAttribute".
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
	dom_nodelist *elementList = NULL;
	dom_element *testEmployee = NULL;
	dom_attr *domesticAttr = NULL;
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

	if (elementList != NULL) {
		dom_nodelist_unref(elementList);
		elementList = NULL;
	}
	exp = dom_document_get_elements_by_tag_name((dom_document *)doc, dstring1, &elementList);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_get_elements_by_tag_name");
		dom_string_unref(dstring1);
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (testEmployee != NULL) {
		dom_node_unref(testEmployee);
		testEmployee = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 0, &testEmployee);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "invalidAttribute";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (domesticAttr != NULL) {
		dom_node_unref(domesticAttr);
		domesticAttr = NULL;
	}
	exp = dom_element_get_attribute_node((dom_element *)testEmployee, dstring2, &domesticAttr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_get_attribute_node");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_null(domesticAttr));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (domesticAttr != NULL) { dom_node_unref(domesticAttr); domesticAttr = NULL; }
	if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
