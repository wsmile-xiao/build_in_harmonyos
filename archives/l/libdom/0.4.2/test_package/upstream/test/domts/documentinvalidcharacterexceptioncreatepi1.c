/*
title: documentinvalidcharacterexceptioncreatepi1
creator: Curt Arnold
description: 

Creating a processing instruction with an empty target should cause an INVALID_CHARACTER_ERR.
date: 2004-03-09
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
	dom_processing_instruction *badPI = NULL;
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
	if(is_contenttype("text/html")) {
	const char *string1 = "foo";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	const char *string2 = "data";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (badPI != NULL) {
		dom_node_unref(badPI);
		badPI = NULL;
	}
	exp = dom_document_create_processing_instruction((dom_document *)doc, dstring1, dstring2, &badPI);
assert(exp == 9);
dom_string_unref(dstring2);
dom_string_unref(dstring1);
	} else {	const char *string3 = "";
	dom_string *dstring3;
	exp = dom_string_create((const uint8_t *)string3,
			strlen(string3), &dstring3);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (badPI != NULL) { dom_node_unref(badPI); badPI = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	const char *string4 = "data";
	dom_string *dstring4;
	exp = dom_string_create((const uint8_t *)string4,
			strlen(string4), &dstring4);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring3);
		if (badPI != NULL) { dom_node_unref(badPI); badPI = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (badPI != NULL) {
		dom_node_unref(badPI);
		badPI = NULL;
	}
	exp = dom_document_create_processing_instruction((dom_document *)doc, dstring3, dstring4, &badPI);
assert(exp == 5);
dom_string_unref(dstring4);
dom_string_unref(dstring3);
}


	if (badPI != NULL) { dom_node_unref(badPI); badPI = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
