/*
title: nodeAppendChildNewChildDiffDocument
creator: NIST
description: 

    The "appendChild(newChild)" method raises a 
    WRONG_DOCUMENT_ERR DOMException if the "newChild" was
    created from a different document than the one that 
    created this node.
    
    Retrieve the second employee and attempt to append    
    a node created from a different document.   An attempt 
    to make such a replacement should raise the desired 
    exception.
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
	dom_document *doc1 = NULL;
	dom_document *doc2 = NULL;
	dom_node *newChild = NULL;
	dom_nodelist *elementList = NULL;
	dom_node *elementNode = NULL;
	dom_node *appendedChild = NULL;
	const char *test1 = "staff.html";

	doc1 = load_html(test1, false);	if (doc1 == NULL) {
		const char *test2 = "staff.xml";

		doc1 = load_xml(test2, false);
		if (doc1 == NULL)
			return 1;
		}
	exp = dom_document_get_implementation((dom_document *) doc1, &doc_impl);
	if (exp != DOM_NO_ERR)
		return exp;
	const char *test3 = "staff.html";

	doc2 = load_html(test3, true);	if (doc2 == NULL) {
		const char *test4 = "staff.xml";

		doc2 = load_xml(test4, true);
		if (doc2 == NULL)
			return 1;
		}
	exp = dom_document_get_implementation((dom_document *) doc2, &doc_impl);
	if (exp != DOM_NO_ERR)
		return exp;
	const char *string1 = "newChild";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

		return exp;
	}

	if (newChild != NULL) {
		dom_node_unref(newChild);
		newChild = NULL;
	}
	exp = dom_document_create_element((dom_document *)doc1, dstring1, &newChild);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_element");
		dom_string_unref(dstring1);
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

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
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

		return exp;
	}

	if (elementList != NULL) {
		dom_nodelist_unref(elementList);
		elementList = NULL;
	}
	exp = dom_document_get_elements_by_tag_name((dom_document *)doc2, dstring2, &elementList);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_get_elements_by_tag_name");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

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
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

		return exp;
	}
	if (appendedChild != NULL) {
		dom_node_unref(appendedChild);
		appendedChild = NULL;
	}
	exp = dom_node_append_child((dom_node *)elementNode, newChild, &appendedChild);
assert(exp == 4);


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
	if (elementNode != NULL) { dom_node_unref(elementNode); elementNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (newChild != NULL) { dom_node_unref(newChild); newChild = NULL; }
	if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
	if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }


	printf("PASS");

	return 0;

}
