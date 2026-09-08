/*
title: hc_documentCreateElementCaseSensitive
creator: Curt Arnold
description: 

    The tagName parameter in the "createElement(tagName)"
   method is case-sensitive for XML documents.
   Retrieve the entire DOM document and invoke its 
   "createElement(tagName)" method twice.  Once for tagName
   equal to "acronym" and once for tagName equal to "ACRONYM"
   Each call should create a distinct Element node.  The
   newly created Elements are then assigned attributes 
   that are retrieved.

   Modified on 27 June 2003 to avoid setting an invalid style
   values and checked the node names to see if they matched expectations.
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
	dom_element *newElement1 = NULL;
	dom_element *newElement2 = NULL;
	dom_string *attribute1 = NULL;
	dom_string *attribute2 = NULL;
	dom_string *nodeName1 = NULL;
	dom_string *nodeName2 = NULL;
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
	const char *string1 = "ACRONYM";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (newElement1 != NULL) {
		dom_node_unref(newElement1);
		newElement1 = NULL;
	}
	exp = dom_document_create_element((dom_document *)doc, dstring1, &newElement1);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_element");
		dom_string_unref(dstring1);
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "acronym";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (newElement2 != NULL) {
		dom_node_unref(newElement2);
		newElement2 = NULL;
	}
	exp = dom_document_create_element((dom_document *)doc, dstring2, &newElement2);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_element");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string3 = "lang";
	dom_string *dstring3;
	exp = dom_string_create((const uint8_t *)string3,
			strlen(string3), &dstring3);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	const char *string4 = "EN";
	dom_string *dstring4;
	exp = dom_string_create((const uint8_t *)string4,
			strlen(string4), &dstring4);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	exp = dom_element_set_attribute((dom_element *)newElement1, dstring3, dstring4);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_set_attribute");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string5 = "title";
	dom_string *dstring5;
	exp = dom_string_create((const uint8_t *)string5,
			strlen(string5), &dstring5);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	const char *string6 = "Dallas";
	dom_string *dstring6;
	exp = dom_string_create((const uint8_t *)string6,
			strlen(string6), &dstring6);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	exp = dom_element_set_attribute((dom_element *)newElement2, dstring5, dstring6);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_set_attribute");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		dom_string_unref(dstring6);
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string7 = "lang";
	dom_string *dstring7;
	exp = dom_string_create((const uint8_t *)string7,
			strlen(string7), &dstring7);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		dom_string_unref(dstring6);
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (attribute1 != NULL) {
		dom_string_unref(attribute1);
		attribute1 = NULL;
	}
	exp = dom_element_get_attribute((dom_element *)newElement1, dstring7, &attribute1);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_get_attribute");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		dom_string_unref(dstring6);
		dom_string_unref(dstring7);
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string8 = "title";
	dom_string *dstring8;
	exp = dom_string_create((const uint8_t *)string8,
			strlen(string8), &dstring8);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		dom_string_unref(dstring6);
		dom_string_unref(dstring7);
		if (attribute1 != NULL) { dom_string_unref(attribute1); attribute1 = NULL; }
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (attribute2 != NULL) {
		dom_string_unref(attribute2);
		attribute2 = NULL;
	}
	exp = dom_element_get_attribute((dom_element *)newElement2, dstring8, &attribute2);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_get_attribute");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		dom_string_unref(dstring6);
		dom_string_unref(dstring7);
		dom_string_unref(dstring8);
		if (attribute1 != NULL) { dom_string_unref(attribute1); attribute1 = NULL; }
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("EN", attribute1, false));
	assert(is_equals_string("Dallas", attribute2, false));
	if (nodeName1 != NULL) {
		dom_string_unref(nodeName1);
		nodeName1 = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)newElement1, &nodeName1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		dom_string_unref(dstring6);
		dom_string_unref(dstring7);
		dom_string_unref(dstring8);
		if (attribute2 != NULL) { dom_string_unref(attribute2); attribute2 = NULL; }
		if (attribute1 != NULL) { dom_string_unref(attribute1); attribute1 = NULL; }
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (nodeName2 != NULL) {
		dom_string_unref(nodeName2);
		nodeName2 = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)newElement2, &nodeName2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		dom_string_unref(dstring4);
		dom_string_unref(dstring5);
		dom_string_unref(dstring6);
		dom_string_unref(dstring7);
		dom_string_unref(dstring8);
		if (nodeName1 != NULL) { dom_string_unref(nodeName1); nodeName1 = NULL; }
		if (attribute2 != NULL) { dom_string_unref(attribute2); attribute2 = NULL; }
		if (attribute1 != NULL) { dom_string_unref(attribute1); attribute1 = NULL; }
		if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
		if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("ACRONYM", nodeName1, true));
	assert(is_equals_string("acronym", nodeName2, true));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	dom_string_unref(dstring3);
	dom_string_unref(dstring4);
	dom_string_unref(dstring5);
	dom_string_unref(dstring6);
	dom_string_unref(dstring7);
	dom_string_unref(dstring8);
	if (nodeName2 != NULL) { dom_string_unref(nodeName2); nodeName2 = NULL; }
	if (nodeName1 != NULL) { dom_string_unref(nodeName1); nodeName1 = NULL; }
	if (attribute2 != NULL) { dom_string_unref(attribute2); attribute2 = NULL; }
	if (attribute1 != NULL) { dom_string_unref(attribute1); attribute1 = NULL; }
	if (newElement2 != NULL) { dom_node_unref(newElement2); newElement2 = NULL; }
	if (newElement1 != NULL) { dom_node_unref(newElement1); newElement1 = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
