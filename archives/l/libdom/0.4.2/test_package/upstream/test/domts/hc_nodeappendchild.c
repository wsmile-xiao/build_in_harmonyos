/*
title: hc_nodeAppendChild
creator: Curt Arnold
description: 

    Retrieve the second "p" and append a "br" Element
    node to the list of children.   The last node in the list
    is then retrieved and its NodeName examined.   The
    "getNodeName()" method should return "br".
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
	dom_node *employeeNode = NULL;
	dom_nodelist *childList = NULL;
	dom_node *createdNode = NULL;
	dom_node *lchild = NULL;
	dom_string *childName = NULL;
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
	const char *string1 = "p";
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
	const char *string2 = "br";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (createdNode != NULL) {
		dom_node_unref(createdNode);
		createdNode = NULL;
	}
	exp = dom_document_create_element((dom_document *)doc, dstring2, &createdNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_element");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (appendedChild != NULL) {
		dom_node_unref(appendedChild);
		appendedChild = NULL;
	}
	exp = dom_node_append_child((dom_node *)employeeNode, createdNode, &appendedChild);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_node_append_child");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (createdNode != NULL) { dom_node_unref(createdNode); createdNode = NULL; }
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (lchild != NULL) {
		dom_node_unref(lchild);
		lchild = NULL;
	}
	exp = dom_node_get_last_child((dom_node *)employeeNode, &lchild);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "lastChild");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
		if (createdNode != NULL) { dom_node_unref(createdNode); createdNode = NULL; }
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (childName != NULL) {
		dom_string_unref(childName);
		childName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)lchild, &childName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (lchild != NULL) { dom_node_unref(lchild); lchild = NULL; }
		if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
		if (createdNode != NULL) { dom_node_unref(createdNode); createdNode = NULL; }
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("br", childName, true));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (childName != NULL) { dom_string_unref(childName); childName = NULL; }
	if (lchild != NULL) { dom_node_unref(lchild); lchild = NULL; }
	if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
	if (createdNode != NULL) { dom_node_unref(createdNode); createdNode = NULL; }
	if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
	if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
