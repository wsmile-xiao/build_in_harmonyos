/*
title: documentCreateCDATASection
creator: NIST
description: 

    The "createCDATASection(data)" method creates a new 
   CDATASection node whose value is the specified string.
   Retrieve the entire DOM document and invoke its 
   "createCDATASection(data)" method.  It should create a
   new CDATASection node whose "data" is the specified 
   string.  The content, name and type are retrieved and
   output.
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
	dom_cdata_section *newCDATASectionNode = NULL;
	dom_string *newCDATASectionValue = NULL;
	dom_string *newCDATASectionName = NULL;
	int32_t newCDATASectionType;
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
	const char *string1 = "This is a new CDATASection node";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (newCDATASectionNode != NULL) {
		dom_node_unref(newCDATASectionNode);
		newCDATASectionNode = NULL;
	}
	exp = dom_document_create_cdata_section((dom_document *)doc, dstring1, &newCDATASectionNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_cdata_section");
		dom_string_unref(dstring1);
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (newCDATASectionValue != NULL) {
		dom_string_unref(newCDATASectionValue);
		newCDATASectionValue = NULL;
	}
	exp = dom_node_get_node_value((dom_node *)newCDATASectionNode, &newCDATASectionValue);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeValue");
		dom_string_unref(dstring1);
		if (newCDATASectionNode != NULL) { dom_node_unref(newCDATASectionNode); newCDATASectionNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("This is a new CDATASection node", newCDATASectionValue, false));
	if (newCDATASectionName != NULL) {
		dom_string_unref(newCDATASectionName);
		newCDATASectionName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)newCDATASectionNode, &newCDATASectionName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		if (newCDATASectionValue != NULL) { dom_string_unref(newCDATASectionValue); newCDATASectionValue = NULL; }
		if (newCDATASectionNode != NULL) { dom_node_unref(newCDATASectionNode); newCDATASectionNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("#cdata-section", newCDATASectionName, false));
	exp = dom_node_get_node_type((dom_node *)newCDATASectionNode, &newCDATASectionType);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeType");
		dom_string_unref(dstring1);
		if (newCDATASectionName != NULL) { dom_string_unref(newCDATASectionName); newCDATASectionName = NULL; }
		if (newCDATASectionValue != NULL) { dom_string_unref(newCDATASectionValue); newCDATASectionValue = NULL; }
		if (newCDATASectionNode != NULL) { dom_node_unref(newCDATASectionNode); newCDATASectionNode = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_int(4, newCDATASectionType, false));


	dom_string_unref(dstring1);
	if (newCDATASectionName != NULL) { dom_string_unref(newCDATASectionName); newCDATASectionName = NULL; }
	if (newCDATASectionValue != NULL) { dom_string_unref(newCDATASectionValue); newCDATASectionValue = NULL; }
	if (newCDATASectionNode != NULL) { dom_node_unref(newCDATASectionNode); newCDATASectionNode = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
