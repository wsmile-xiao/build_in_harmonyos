/*
title: documentGetRootNode
creator: NIST
description: 

    The "getDocumentElement()" method provides direct access 
   to the child node that is the root element of the document.
   Retrieve the entire DOM document and invoke its 
   "getDocumentElement()" method.  It should return an
   Element node whose NodeName is "staff" (or "svg").
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
	dom_element *root = NULL;
	dom_string *rootName = NULL;
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
	if (root != NULL) {
		dom_node_unref(root);
		root = NULL;
	}
	exp = dom_document_get_document_element((dom_document *)doc, &root);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "documentElement");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (rootName != NULL) {
		dom_string_unref(rootName);
		rootName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)root, &rootName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		if (root != NULL) { dom_node_unref(root); root = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if(is_contenttype("image/svg+xml")) {
	assert(is_equals_string("svg", rootName, false));
	} else {	assert(is_equals_string("staff", rootName, false));
}


	if (rootName != NULL) { dom_string_unref(rootName); rootName = NULL; }
	if (root != NULL) { dom_node_unref(root); root = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
