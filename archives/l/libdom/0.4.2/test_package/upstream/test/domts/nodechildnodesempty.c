/*
title: nodeChildNodesEmpty
creator: NIST
description: 

    The "getChildNodes()" method returns a NodeList
    that contains all children of this node.   If there
    are not any children, this is a NodeList that does not 
    contain any nodes. 

    Retrieve the Text node from the second child of the second
    employee and invoke the "getChildNodes()" method.   The
    NodeList returned should not have any nodes.
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
	dom_node *employeeNode = NULL;
	dom_nodelist *childList = NULL;
	dom_node *secondCNode = NULL;
	dom_node *textNode = NULL;
	dom_nodelist *childNodesList = NULL;
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
	const char *string1 = "employee";
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
	if (employeeNode != NULL) {
		dom_node_unref(employeeNode);
		employeeNode = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 1, &employeeNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (childList != NULL) {
		dom_nodelist_unref(childList);
		childList = NULL;
	}
	exp = dom_node_get_child_nodes((dom_node *)employeeNode, &childList);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "childNodes");
		dom_string_unref(dstring1);
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (secondCNode != NULL) {
		dom_node_unref(secondCNode);
		secondCNode = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)childList, 1, &secondCNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (textNode != NULL) {
		dom_node_unref(textNode);
		textNode = NULL;
	}
	exp = dom_node_get_first_child((dom_node *)secondCNode, &textNode);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "firstChild");
		dom_string_unref(dstring1);
		if (secondCNode != NULL) { dom_node_unref(secondCNode); secondCNode = NULL; }
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (childNodesList != NULL) {
		dom_nodelist_unref(childNodesList);
		childNodesList = NULL;
	}
	exp = dom_node_get_child_nodes((dom_node *)textNode, &childNodesList);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "childNodes");
		dom_string_unref(dstring1);
		if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
		if (secondCNode != NULL) { dom_node_unref(secondCNode); secondCNode = NULL; }
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_size_domnodelist(0, childNodesList));


	dom_string_unref(dstring1);
	if (childNodesList != NULL) { dom_nodelist_unref(childNodesList); childNodesList = NULL; }
	if (textNode != NULL) { dom_node_unref(textNode); textNode = NULL; }
	if (secondCNode != NULL) { dom_node_unref(secondCNode); secondCNode = NULL; }
	if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
	if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
