/*
title: hc_elementgettagname
creator: Curt Arnold
description: 

   Invoke the "getTagName()" method one the 
   root node. The value returned should be "html" or "svg". 
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
	dom_element *root = NULL;
	dom_string *tagname = NULL;
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
	if (tagname != NULL) {
		dom_string_unref(tagname);
		tagname = NULL;
	}
	exp = dom_element_get_tag_name((dom_element *)root, &tagname);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "tagName");
		if (root != NULL) { dom_node_unref(root); root = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if(is_contenttype("image/svg+xml")) {
	assert(is_equals_string("svg", tagname, false));
	} else {	assert(is_equals_string("html", tagname, true));
}


	if (tagname != NULL) { dom_string_unref(tagname); tagname = NULL; }
	if (root != NULL) { dom_node_unref(root); root = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
