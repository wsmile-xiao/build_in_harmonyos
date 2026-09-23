/*
title: hc_nodevalue02
creator: Curt Arnold
description: 

An comment is created, setNodeValue is called with a non-null argument, but getNodeValue
should still return null.
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
	dom_node *newNode = NULL;
	dom_string *newValue = NULL;
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
	const char *string1 = "This is a new Comment node";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (newNode != NULL) {
		dom_node_unref(newNode);
		newNode = NULL;
	}
	exp = dom_document_create_comment((dom_document *)doc, dstring1, &newNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_comment");
		dom_string_unref(dstring1);
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (newValue != NULL) {
		dom_string_unref(newValue);
		newValue = NULL;
	}
	exp = dom_node_get_node_value((dom_node *)newNode, &newValue);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeValue");
		dom_string_unref(dstring1);
		if (newNode != NULL) { dom_node_unref(newNode); newNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("This is a new Comment node", newValue, false));
	const char *string2 = "This should have an effect";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (newValue != NULL) { dom_string_unref(newValue); newValue = NULL; }
		if (newNode != NULL) { dom_node_unref(newNode); newNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

exp = dom_node_set_node_value(newNode, dstring2);		if (exp != DOM_NO_ERR) {
			fprintf(stderr, "Exception raised when fetch attribute %s", "nodeValue");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newValue != NULL) { dom_string_unref(newValue); newValue = NULL; }
		if (newNode != NULL) { dom_node_unref(newNode); newNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

			return exp;
		}
	if (newValue != NULL) {
		dom_string_unref(newValue);
		newValue = NULL;
	}
	exp = dom_node_get_node_value((dom_node *)newNode, &newValue);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeValue");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newValue != NULL) { dom_string_unref(newValue); newValue = NULL; }
		if (newNode != NULL) { dom_node_unref(newNode); newNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("This should have an effect", newValue, false));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (newValue != NULL) { dom_string_unref(newValue); newValue = NULL; }
	if (newNode != NULL) { dom_node_unref(newNode); newNode = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
