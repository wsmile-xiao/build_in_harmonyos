/*
title: characterdataIndexSizeErrSubstringNegativeOffset
creator: NIST
description: 

    The "substringData(offset,count)" method raises an
   INDEX_SIZE_ERR DOMException if the specified offset
   is negative. 
   
   Retrieve the character data of the last child of the
   first employee and invoke its "substringData(offset,count)
   method with offset=-5 and count=3.  It should raise the
   desired exception since the offset is negative.
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
	dom_nodelist *elementList = NULL;
	dom_node *nameNode = NULL;
	dom_characterdata *child = NULL;
	dom_string *badString = NULL;
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
	const char *string1 = "address";
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
	if (nameNode != NULL) {
		dom_node_unref(nameNode);
		nameNode = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 0, &nameNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (child != NULL) {
		dom_node_unref(child);
		child = NULL;
	}
	exp = dom_node_get_first_child((dom_node *)nameNode, &child);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "firstChild");
		dom_string_unref(dstring1);
		if (nameNode != NULL) { dom_node_unref(nameNode); nameNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (badString != NULL) {
		dom_string_unref(badString);
		badString = NULL;
	}
	exp = dom_characterdata_substring_data((dom_characterdata *)child, -5, 3, &badString);
assert(exp == 1);


	dom_string_unref(dstring1);
	if (badString != NULL) { dom_string_unref(badString); badString = NULL; }
	if (child != NULL) { dom_node_unref(child); child = NULL; }
	if (nameNode != NULL) { dom_node_unref(nameNode); nameNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
