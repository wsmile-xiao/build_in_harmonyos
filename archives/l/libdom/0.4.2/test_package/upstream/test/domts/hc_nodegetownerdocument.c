/*
title: hc_nodegetownerdocument
creator: Curt Arnold
description: 

Evaluate Node.ownerDocument on the second "p" element.
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
	dom_nodelist *elementList = NULL;
	dom_node *docNode = NULL;
	dom_document *ownerDocument = NULL;
	dom_element *docElement = NULL;
	dom_string *elementName = NULL;
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
	const char *string1 = "p";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (elementList != NULL) {
		dom_nodelist_unref(elementList);
		elementList = NULL;
	}
	exp = dom_document_get_elements_by_tag_name((dom_document *)doc, dstring1, &elementList);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_get_elements_by_tag_name");
		dom_string_unref(dstring1);
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (docNode != NULL) {
		dom_node_unref(docNode);
		docNode = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 1, &docNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (ownerDocument != NULL) {
		dom_node_unref(ownerDocument);
		ownerDocument = NULL;
	}
	exp = dom_node_get_owner_document((dom_node *)docNode, &ownerDocument);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "ownerDocument");
		dom_string_unref(dstring1);
		if (docNode != NULL) { dom_node_unref(docNode); docNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (docElement != NULL) {
		dom_node_unref(docElement);
		docElement = NULL;
	}
	exp = dom_document_get_document_element((dom_document *)ownerDocument, &docElement);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "documentElement");
		dom_string_unref(dstring1);
		if (ownerDocument != NULL) { dom_node_unref(ownerDocument); ownerDocument = NULL; }
		if (docNode != NULL) { dom_node_unref(docNode); docNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (elementName != NULL) {
		dom_string_unref(elementName);
		elementName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)docElement, &elementName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		if (docElement != NULL) { dom_node_unref(docElement); docElement = NULL; }
		if (ownerDocument != NULL) { dom_node_unref(ownerDocument); ownerDocument = NULL; }
		if (docNode != NULL) { dom_node_unref(docNode); docNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if(is_contenttype("image/svg+xml")) {
	assert(is_equals_string("svg", elementName, false));
	} else {	assert(is_equals_string("html", elementName, true));
}


	dom_string_unref(dstring1);
	if (elementName != NULL) { dom_string_unref(elementName); elementName = NULL; }
	if (docElement != NULL) { dom_node_unref(docElement); docElement = NULL; }
	if (ownerDocument != NULL) { dom_node_unref(ownerDocument); ownerDocument = NULL; }
	if (docNode != NULL) { dom_node_unref(docNode); docNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
