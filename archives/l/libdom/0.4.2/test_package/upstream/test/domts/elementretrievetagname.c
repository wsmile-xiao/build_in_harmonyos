/*
title: elementRetrieveTagName
creator: NIST
description: 

    The "getElementsByTagName()" method returns a NodeList 
   of all descendant elements with a given tagName.    
   
   Invoke the "getElementsByTagName()" method and create
   a NodeList of "position" elements.  Retrieve the second 
   "position" element in the list and return the NodeName. 
contributor: Mary Brady
date: 2001-08-17
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
	dom_node *testEmployee = NULL;
	dom_string *name = NULL;
	const char *test1 = "staff.html";

	doc = load_html(test1, false);	if (doc == NULL) {
		const char *test2 = "staff.xml";

		doc = load_xml(test2, false);
		if (doc == NULL)
			return 1;
		}
	exp = dom_document_get_implementation((dom_document *) doc, &doc_impl);
	if (exp != DOM_NO_ERR)
		return exp;
	const char *string1 = "position";
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
	exp = dom_nodelist_item((dom_nodelist *)elementList, 1, &testEmployee);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (name != NULL) {
		dom_string_unref(name);
		name = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)testEmployee, &name);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("position", name, false));
	if (name != NULL) {
		dom_string_unref(name);
		name = NULL;
	}
	exp = dom_element_get_tag_name((dom_element *)testEmployee, &name);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "tagName");
		dom_string_unref(dstring1);
		if (name != NULL) { dom_string_unref(name); name = NULL; }
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("position", name, false));


	dom_string_unref(dstring1);
	if (name != NULL) { dom_string_unref(name); name = NULL; }
	if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
