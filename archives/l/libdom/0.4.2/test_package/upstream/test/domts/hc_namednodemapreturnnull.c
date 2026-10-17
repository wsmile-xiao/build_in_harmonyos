/*
title: hc_namednodemapReturnNull
creator: Curt Arnold
description: 

    The "getNamedItem(name)" method returns null of the 
   specified name did not identify any node in the map. 
   
   Retrieve the second employee and create a NamedNodeMap 
   listing of the attributes of the last child.  Once the
   list is created an invocation of the "getNamedItem(name)"
   method is done with name="lang".  This name does not 
   match any names in the list therefore the method should
   return null.
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
	dom_node *testEmployee = NULL;
	dom_namednodemap *attributes = NULL;
	dom_attr *districtNode = NULL;
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
	if (attributes != NULL) {
		dom_namednodemap_unref(attributes);
		attributes = NULL;
	}
	exp = dom_node_get_attributes((dom_node *)testEmployee, &attributes);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "attributes");
		dom_string_unref(dstring1);
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "lang";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (districtNode != NULL) {
		dom_node_unref(districtNode);
		districtNode = NULL;
	}
	exp = dom_namednodemap_get_named_item((dom_namednodemap *)attributes, dstring2, &districtNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_namednodemap_get_named_item");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_null(districtNode));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (districtNode != NULL) { dom_node_unref(districtNode); districtNode = NULL; }
	if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
	if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
