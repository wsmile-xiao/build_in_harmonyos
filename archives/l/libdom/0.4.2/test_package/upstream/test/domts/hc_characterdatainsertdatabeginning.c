/*
title: hc_characterdataInsertDataBeginning
creator: Curt Arnold
description: 

The "insertData(offset,arg)" method will insert a string
at the specified character offset.  Insert the data at
the beginning of the character data.

Retrieve the character data from the second child of
the first employee.  The "insertData(offset,arg)"
method is then called with offset=0 and arg="Mss.".
The method should insert the string "Mss." at position 0.
The new value of the character data should be
"Mss. Margaret Martin".
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
	dom_node *nameNode = NULL;
	dom_characterdata *child = NULL;
	dom_string *childData = NULL;
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
	const char *string1 = "strong";
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
	const char *string2 = "Mss. ";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (child != NULL) { dom_node_unref(child); child = NULL; }
		if (nameNode != NULL) { dom_node_unref(nameNode); nameNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	exp = dom_characterdata_insert_data((dom_characterdata *)child, 0, dstring2);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_characterdata_insert_data");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (child != NULL) { dom_node_unref(child); child = NULL; }
		if (nameNode != NULL) { dom_node_unref(nameNode); nameNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (childData != NULL) {
		dom_string_unref(childData);
		childData = NULL;
	}
	exp = dom_characterdata_get_data((dom_characterdata *)child, &childData);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "data");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (child != NULL) { dom_node_unref(child); child = NULL; }
		if (nameNode != NULL) { dom_node_unref(nameNode); nameNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("Mss. Margaret Martin", childData, false));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (childData != NULL) { dom_string_unref(childData); childData = NULL; }
	if (child != NULL) { dom_node_unref(child); child = NULL; }
	if (nameNode != NULL) { dom_node_unref(nameNode); nameNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
