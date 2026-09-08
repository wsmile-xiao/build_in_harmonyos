/*
title: nodeAttributeNodeValue
creator: NIST
description: 


    The string returned by the "getNodeValue()" method for an 

    Attribute Node is the value of the Attribute.

    

    Retrieve the Attribute named "domestic" from the last 

    child of the first employee and check the string returned 

    by the "getNodeValue()" method.   It should be equal to 

    "Yes". 

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
	dom_element *testAddr = NULL;
	dom_attr *addrAttr = NULL;
	dom_string *attrValue = NULL;
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
	const char *string1 = "address";
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
	if (testAddr != NULL) {
		dom_node_unref(testAddr);
		testAddr = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 0, &testAddr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "domestic";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (testAddr != NULL) { dom_node_unref(testAddr); testAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (addrAttr != NULL) {
		dom_node_unref(addrAttr);
		addrAttr = NULL;
	}
	exp = dom_element_get_attribute_node((dom_element *)testAddr, dstring2, &addrAttr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_get_attribute_node");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (testAddr != NULL) { dom_node_unref(testAddr); testAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (attrValue != NULL) {
		dom_string_unref(attrValue);
		attrValue = NULL;
	}
	exp = dom_node_get_node_value((dom_node *)addrAttr, &attrValue);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeValue");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (addrAttr != NULL) { dom_node_unref(addrAttr); addrAttr = NULL; }
		if (testAddr != NULL) { dom_node_unref(testAddr); testAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("Yes", attrValue, false));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (attrValue != NULL) { dom_string_unref(attrValue); attrValue = NULL; }
	if (addrAttr != NULL) { dom_node_unref(addrAttr); addrAttr = NULL; }
	if (testAddr != NULL) { dom_node_unref(testAddr); testAddr = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
