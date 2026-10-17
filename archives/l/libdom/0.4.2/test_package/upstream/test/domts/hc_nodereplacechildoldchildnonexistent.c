/*
title: hc_nodeReplaceChildOldChildNonexistent
creator: Curt Arnold
description: 

    The "replaceChild(newChild,oldChild)" method raises a 
    NOT_FOUND_ERR DOMException if the old child is
    not a child of this node.
    
    Retrieve the second employee and attempt to replace a
    node that is not one of its children.   An attempt to
    replace such a node should raise the desired exception.
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
	dom_node *oldChild = NULL;
	dom_node *newChild = NULL;
	dom_nodelist *elementList = NULL;
	dom_node *elementNode = NULL;
	dom_node *replacedNode = NULL;
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
	const char *string1 = "br";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (newChild != NULL) {
		dom_node_unref(newChild);
		newChild = NULL;
	}
	exp = dom_document_create_element((dom_document *)doc, dstring1, &newChild);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_element");
		dom_string_unref(dstring1);
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "b";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (oldChild != NULL) {
		dom_node_unref(oldChild);
		oldChild = NULL;
	}
	exp = dom_document_create_element((dom_document *)doc, dstring2, &oldChild);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_element");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string3 = "p";
	dom_string *dstring3;
	exp = dom_string_create((const uint8_t *)string3,
			strlen(string3), &dstring3);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (oldChild != NULL) { dom_node_unref(oldChild); oldChild = NULL; }
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (elementList != NULL) {
		dom_nodelist_unref(elementList);
		elementList = NULL;
	}
	exp = dom_document_get_elements_by_tag_name((dom_document *)doc, dstring3, &elementList);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_get_elements_by_tag_name");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (oldChild != NULL) { dom_node_unref(oldChild); oldChild = NULL; }
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (elementNode != NULL) {
		dom_node_unref(elementNode);
		elementNode = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 1, &elementNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (oldChild != NULL) { dom_node_unref(oldChild); oldChild = NULL; }
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (replacedNode != NULL) {
		dom_node_unref(replacedNode);
		replacedNode = NULL;
	}
	exp = dom_node_replace_child((dom_node *)elementNode, newChild, oldChild, &replacedNode);
assert(exp == 8);


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	dom_string_unref(dstring3);
	if (replacedNode != NULL) { dom_node_unref(replacedNode); replacedNode = NULL; }
	if (elementNode != NULL) { dom_node_unref(elementNode); elementNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (oldChild != NULL) { dom_node_unref(oldChild); oldChild = NULL; }
	if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
