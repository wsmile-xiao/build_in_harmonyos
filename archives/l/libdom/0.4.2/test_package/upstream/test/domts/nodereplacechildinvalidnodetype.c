/*
title: nodeReplaceChildInvalidNodeType
creator: NIST
description: 

    The "replaceChild(newChild,oldChild)" method raises a 
    HIERARCHY_REQUEST_ERR DOMException if this node is of
    a type that does not allow children of the type "newChild"
    to be inserted.
    
    Retrieve the root node and attempt to replace 
    one of its children with a newly created Attr node.
    An Element node cannot have children of the "Attr"
    type, therefore the desired exception should be raised.
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
	dom_element *rootNode = NULL;
	dom_node *newChild = NULL;
	dom_nodelist *elementList = NULL;
	dom_node *oldChild = NULL;
	dom_node *replacedChild = NULL;
	const char *test1 = "staff.html";

	doc = load_html(test1, true);	if (doc == NULL) {
		const char *test2 = "staff.xml";

		doc = load_xml(test2, true);
		if (doc == NULL)
			return 1;
		}
	exp = dom_document_get_implementation((dom_document *) doc, &doc_impl);
	if (exp != DOM_NO_ERR)
		return exp;
	if (rootNode != NULL) {
		dom_node_unref(rootNode);
		rootNode = NULL;
	}
	exp = dom_document_get_document_element((dom_document *)doc, &rootNode);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "documentElement");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string1 = "newAttribute";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (rootNode != NULL) { dom_node_unref(rootNode); rootNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (newChild != NULL) {
		dom_node_unref(newChild);
		newChild = NULL;
	}
	exp = dom_document_create_attribute((dom_document *)doc, dstring1, &newChild);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_attribute");
		dom_string_unref(dstring1);
		if (rootNode != NULL) { dom_node_unref(rootNode); rootNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "employee";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (rootNode != NULL) { dom_node_unref(rootNode); rootNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (elementList != NULL) {
		dom_nodelist_unref(elementList);
		elementList = NULL;
	}
	exp = dom_document_get_elements_by_tag_name((dom_document *)doc, dstring2, &elementList);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_get_elements_by_tag_name");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (rootNode != NULL) { dom_node_unref(rootNode); rootNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (oldChild != NULL) {
		dom_node_unref(oldChild);
		oldChild = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 1, &oldChild);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (rootNode != NULL) { dom_node_unref(rootNode); rootNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (replacedChild != NULL) {
		dom_node_unref(replacedChild);
		replacedChild = NULL;
	}
	exp = dom_node_replace_child((dom_node *)rootNode, newChild, oldChild, &replacedChild);
assert(exp == 3);


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (replacedChild != NULL) { dom_node_unref(replacedChild); replacedChild = NULL; }
	if (oldChild != NULL) { dom_node_unref(oldChild); oldChild = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
	if (rootNode != NULL) { dom_node_unref(rootNode); rootNode = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
