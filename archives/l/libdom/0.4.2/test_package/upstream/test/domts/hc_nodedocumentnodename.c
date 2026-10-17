/*
title: hc_nodeDocumentNodeName
creator: Curt Arnold
description: 

    The string returned by the "getNodeName()" method for a 
    Document Node is "#document".

    Retrieve the DOM document and check the string returned
    by the "getNodeName()" method.   It should be equal to 
    "#document".
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
	dom_string *documentName = NULL;
	const char *test1 = "hc_staff.html";

	doc = load_html(test1, false);	if (doc == NULL) {
		const char *test2 = "hc_staff.xml";

		doc = load_xml(test2, false);
		if (doc == NULL)
			return 1;
		}
	exp = dom_document_get_implementation((dom_document *) doc, &doc_impl);
	if (exp != DOM_NO_ERR)
		return exp;
	if (documentName != NULL) {
		dom_string_unref(documentName);
		documentName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)doc, &documentName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("#document", documentName, false));


	if (documentName != NULL) { dom_string_unref(documentName); documentName = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
