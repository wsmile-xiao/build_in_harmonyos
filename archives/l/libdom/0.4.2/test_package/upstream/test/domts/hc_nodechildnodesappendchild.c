/*
title: hc_nodeChildNodesAppendChild
creator: Curt Arnold
description: 

    The NodeList returned by the "getChildNodes()" method
    is live.   Changes on the node's children are immediately
    reflected on the nodes returned in the NodeList.
    
    Create a NodeList of the children of the second employee
    and then add a newly created element that was created
    by the "createElement()" method(Document Interface) to
    the second employee by using the "appendChild()" method.
    The length of the NodeList should reflect this new
    addition to the child list.   It should return the value 14.
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
	dom_node *childNode = NULL;
	dom_string *childName = NULL;
	int32_t childType;
	dom_node *textNode = NULL;
	list *actual = NULL;
	list *expected = NULL;
const char *expectedArray[] = { "em", "strong", "code", "sup", "var", "acronym", "br"};
expected = list_new(STRING);
actual = list_new(DOM_STRING);
list_add(expected, *(char **)(expectedArray + 0));
list_add(expected, *(char **)(expectedArray + 1));
list_add(expected, *(char **)(expectedArray + 2));
list_add(expected, *(char **)(expectedArray + 3));
list_add(expected, *(char **)(expectedArray + 4));
list_add(expected, *(char **)(expectedArray + 5));
list_add(expected, *(char **)(expectedArray + 6));
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
dom_node * tnode1 = NULL;	exp = dom_node_append_child((dom_node *)employeeNode, createdNode, &tnode1);
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
dom_node_unref(employeeNode);
employeeNode = tnode1;unsigned int iterator1 = 0;foreach_initialise_domnodelist(childList, &iterator1);
while(get_next_domnodelist(childList, &iterator1, &childNode)) {
	if (childName != NULL) {
		dom_string_unref(childName);
		childName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)childNode, &childName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (childNode != NULL) { dom_node_unref(childNode); childNode = NULL; }
		if (createdNode != NULL) { dom_node_unref(createdNode); createdNode = NULL; }
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	exp = dom_node_get_node_type((dom_node *)childNode, &childType);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeType");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (childName != NULL) { dom_string_unref(childName); childName = NULL; }
		if (childNode != NULL) { dom_node_unref(childNode); childNode = NULL; }
		if (createdNode != NULL) { dom_node_unref(createdNode); createdNode = NULL; }
		if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
		if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if(is_equals_int(1, childType, false)) {
list_add(actual, childName);
	} else {	assert(is_equals_int(3, childType, false));
}
if (childNode != NULL) {
    dom_node_unref(childNode);
    childNode = NULL;
}
}
	assert(is_equals_list(expected, actual, true));


	if (expected != NULL)
		list_destroy(expected);
	if (actual != NULL)
		list_destroy(actual);
	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (childName != NULL) { dom_string_unref(childName); childName = NULL; }
	if (childNode != NULL) { dom_node_unref(childNode); childNode = NULL; }
	if (createdNode != NULL) { dom_node_unref(createdNode); createdNode = NULL; }
	if (childList != NULL) { dom_nodelist_unref(childList); childList = NULL; }
	if (employeeNode != NULL) { dom_node_unref(employeeNode); employeeNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
