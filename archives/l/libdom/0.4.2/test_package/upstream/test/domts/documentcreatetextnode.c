/*
title: documentCreateTextNode
creator: NIST
description: 

    The "createTextNode(data)" method creates a Text node 
   given the specfied string.
   Retrieve the entire DOM document and invoke its 
   "createTextNode(data)" method.  It should create a 
   new Text node whose "data" is the specified string.
   The NodeName and NodeType are also checked.
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
	dom_text *newTextNode = NULL;
	dom_string *newTextName = NULL;
	dom_string *newTextValue = NULL;
	int32_t newTextType;
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
	const char *string1 = "This is a new Text node";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (newTextNode != NULL) {
		dom_node_unref(newTextNode);
		newTextNode = NULL;
	}
	exp = dom_document_create_text_node((dom_document *)doc, dstring1, &newTextNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_text_node");
		dom_string_unref(dstring1);
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (newTextValue != NULL) {
		dom_string_unref(newTextValue);
		newTextValue = NULL;
	}
	exp = dom_node_get_node_value((dom_node *)newTextNode, &newTextValue);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeValue");
		dom_string_unref(dstring1);
		if (newTextNode != NULL) { dom_node_unref(newTextNode); newTextNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("This is a new Text node", newTextValue, false));
	if (newTextName != NULL) {
		dom_string_unref(newTextName);
		newTextName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)newTextNode, &newTextName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		if (newTextValue != NULL) { dom_string_unref(newTextValue); newTextValue = NULL; }
		if (newTextNode != NULL) { dom_node_unref(newTextNode); newTextNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("#text", newTextName, false));
	exp = dom_node_get_node_type((dom_node *)newTextNode, &newTextType);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeType");
		dom_string_unref(dstring1);
		if (newTextName != NULL) { dom_string_unref(newTextName); newTextName = NULL; }
		if (newTextValue != NULL) { dom_string_unref(newTextValue); newTextValue = NULL; }
		if (newTextNode != NULL) { dom_node_unref(newTextNode); newTextNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_int(3, newTextType, false));


	dom_string_unref(dstring1);
	if (newTextName != NULL) { dom_string_unref(newTextName); newTextName = NULL; }
	if (newTextValue != NULL) { dom_string_unref(newTextValue); newTextValue = NULL; }
	if (newTextNode != NULL) { dom_node_unref(newTextNode); newTextNode = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
