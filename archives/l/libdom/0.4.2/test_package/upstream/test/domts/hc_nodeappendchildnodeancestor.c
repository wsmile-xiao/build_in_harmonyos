/*
title: hc_nodeAppendChildNodeAncestor
creator: Curt Arnold
description: 

    The "appendChild(newChild)" method raises a 
    HIERARCHY_REQUEST_ERR DOMException if the node to 
    append is one of this node's ancestors.
    
    Retrieve the second employee and attempt to append 
    an ancestor node(root node) to it.
    An attempt to make such an addition should raise the 
    desired exception.
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
	dom_node *newChild = NULL;
	dom_nodelist *elementList = NULL;
	dom_node *employeeNode = NULL;
	dom_nodelist *childList = NULL;
	dom_node *oldChild = NULL;
	dom_node *appendedChild = NULL;
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
	if (newChild != NULL) {
		dom_node_unref(newChild);
		newChild = NULL;
	}
	exp = dom_document_get_document_element((dom_document *)doc, &newChild);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "documentElement");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string1 = "p";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
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
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
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
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (appendedChild != NULL) {
		dom_node_unref(appendedChild);
		appendedChild = NULL;
	}
	exp = dom_node_append_child((dom_node *)employeeNode, newChild, &appendedChild);
assert(exp == 3);


	dom_string_unref(dstring1);
	if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
	if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
