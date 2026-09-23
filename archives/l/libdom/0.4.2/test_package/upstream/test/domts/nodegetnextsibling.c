/*
title: nodegetnextsibling
creator: NIST
description: 

    The "getNextSibling()" method returns the node immediately
    following this node. 
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
	dom_node *employeeIdNode = NULL;
	dom_node *nsNode = NULL;
	dom_string *nsName = NULL;
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
	const char *string1 = "employeeId";
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
	if (employeeIdNode != NULL) {
		dom_node_unref(employeeIdNode);
		employeeIdNode = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 1, &employeeIdNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (nsNode != NULL) {
		dom_node_unref(nsNode);
		nsNode = NULL;
	}
	exp = dom_node_get_next_sibling((dom_node *)employeeIdNode, &nsNode);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nextSibling");
		dom_string_unref(dstring1);
		if (employeeIdNode != NULL) { dom_node_unref(employeeIdNode); employeeIdNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (nsName != NULL) {
		dom_string_unref(nsName);
		nsName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)nsNode, &nsName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		if (nsNode != NULL) { dom_node_unref(nsNode); nsNode = NULL; }
		if (employeeIdNode != NULL) { dom_node_unref(employeeIdNode); employeeIdNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if(is_equals_string("#text", nsName, false)) {
	dom_node * tnode1 = NULL;
	exp = dom_node_get_next_sibling((dom_node *)nsNode, &tnode1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nextSibling");
		dom_string_unref(dstring1);
		if (nsName != NULL) { dom_string_unref(nsName); nsName = NULL; }
		if (nsNode != NULL) { dom_node_unref(nsNode); nsNode = NULL; }
		if (employeeIdNode != NULL) { dom_node_unref(employeeIdNode); employeeIdNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
dom_node_unref(nsNode);
nsNode = tnode1;	if (nsName != NULL) {
		dom_string_unref(nsName);
		nsName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)nsNode, &nsName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		if (nsName != NULL) { dom_string_unref(nsName); nsName = NULL; }
		if (nsNode != NULL) { dom_node_unref(nsNode); nsNode = NULL; }
		if (employeeIdNode != NULL) { dom_node_unref(employeeIdNode); employeeIdNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
}
	assert(is_equals_string("name", nsName, false));


	dom_string_unref(dstring1);
	if (nsName != NULL) { dom_string_unref(nsName); nsName = NULL; }
	if (nsNode != NULL) { dom_node_unref(nsNode); nsNode = NULL; }
	if (employeeIdNode != NULL) { dom_node_unref(employeeIdNode); employeeIdNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
