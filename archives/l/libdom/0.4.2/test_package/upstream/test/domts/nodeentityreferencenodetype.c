/*
title: nodeEntityReferenceNodeType
creator: NIST
description: 

    The "getNodeType()" method for an EntityReference Node
    returns the constant value 5.
    
    Retrieve the EntityReference node from the last child
    of the second employee and invoke the "getNodeType()"   
    method.   The method should return 5. 
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
	dom_element *entRefAddr = NULL;
	dom_node *entRefNode = NULL;
	int32_t nodeType;
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
	if (entRefAddr != NULL) {
		dom_node_unref(entRefAddr);
		entRefAddr = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 1, &entRefAddr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (entRefNode != NULL) {
		dom_node_unref(entRefNode);
		entRefNode = NULL;
	}
	exp = dom_node_get_first_child((dom_node *)entRefAddr, &entRefNode);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "firstChild");
		dom_string_unref(dstring1);
		if (entRefAddr != NULL) { dom_node_unref(entRefAddr); entRefAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	exp = dom_node_get_node_type((dom_node *)entRefNode, &nodeType);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeType");
		dom_string_unref(dstring1);
		if (entRefNode != NULL) { dom_node_unref(entRefNode); entRefNode = NULL; }
		if (entRefAddr != NULL) { dom_node_unref(entRefAddr); entRefAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if(is_equals_int(3, nodeType, false)) {
	const char *string2 = "ent2";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (entRefNode != NULL) { dom_node_unref(entRefNode); entRefNode = NULL; }
		if (entRefAddr != NULL) { dom_node_unref(entRefAddr); entRefAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (entRefNode != NULL) {
		dom_node_unref(entRefNode);
		entRefNode = NULL;
	}
	exp = dom_document_create_entity_reference((dom_document *)doc, dstring2, &entRefNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_entity_reference");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (entRefNode != NULL) { dom_node_unref(entRefNode); entRefNode = NULL; }
		if (entRefAddr != NULL) { dom_node_unref(entRefAddr); entRefAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert((false == is_null(entRefNode)));
	exp = dom_node_get_node_type((dom_node *)entRefNode, &nodeType);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeType");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (entRefNode != NULL) { dom_node_unref(entRefNode); entRefNode = NULL; }
		if (entRefAddr != NULL) { dom_node_unref(entRefAddr); entRefAddr = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
dom_string_unref(dstring2);
}
	assert(is_equals_int(5, nodeType, false));


	dom_string_unref(dstring1);
	if (entRefNode != NULL) { dom_node_unref(entRefNode); entRefNode = NULL; }
	if (entRefAddr != NULL) { dom_node_unref(entRefAddr); entRefAddr = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
