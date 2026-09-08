/*
title: nodeElementNodeAttributes
creator: NIST
description: 

    The "getAttributes()" method invoked on an Element
    Node returns a NamedNodeMap containing the attributes
    of this node.
    
    Retrieve the last child of the third employee and
    invoke the "getAttributes()" method.   It should return
    a NamedNodeMap containing the attributes of the Element
    node. 
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
	dom_namednodemap *addrAttr = NULL;
	dom_node *attrNode = NULL;
	dom_string *attrName = NULL;
	list *attrList = NULL;
	list *expected = NULL;
const char *expectedArray[] = { "domestic", "street"};
expected = list_new(STRING);
attrList = list_new(DOM_STRING);
list_add(expected, *(char **)(expectedArray + 0));
list_add(expected, *(char **)(expectedArray + 1));
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
	exp = dom_nodelist_item((dom_nodelist *)elementList, 2, &testAddr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (addrAttr != NULL) {
		dom_namednodemap_unref(addrAttr);
		addrAttr = NULL;
	}
	exp = dom_node_get_attributes((dom_node *)testAddr, &addrAttr);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "attributes");
		dom_string_unref(dstring1);
		if (testAddr != NULL) { dom_node_unref(testAddr); testAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
unsigned int iterator1 = 0;foreach_initialise_domnamednodemap(addrAttr, &iterator1);
while(get_next_domnamednodemap(addrAttr, &iterator1, &attrNode)) {
	if (attrName != NULL) {
		dom_string_unref(attrName);
		attrName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)attrNode, &attrName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		if (attrNode != NULL) { dom_node_unref(attrNode); attrNode = NULL; }
		if (addrAttr != NULL) { dom_namednodemap_unref(addrAttr); addrAttr = NULL; }
		if (testAddr != NULL) { dom_node_unref(testAddr); testAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
list_add(attrList, attrName);
if (attrNode != NULL) {
    dom_node_unref(attrNode);
    attrNode = NULL;
}
}
	assert(is_equals_list(expected, attrList, false));


	if (expected != NULL)
		list_destroy(expected);
	if (attrList != NULL)
		list_destroy(attrList);
	dom_string_unref(dstring1);
	if (attrName != NULL) { dom_string_unref(attrName); attrName = NULL; }
	if (attrNode != NULL) { dom_node_unref(attrNode); attrNode = NULL; }
	if (addrAttr != NULL) { dom_namednodemap_unref(addrAttr); addrAttr = NULL; }
	if (testAddr != NULL) { dom_node_unref(testAddr); testAddr = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
