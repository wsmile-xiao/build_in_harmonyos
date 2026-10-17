/*
title: characterdataAppendData
creator: NIST
description: 

    The "appendData(arg)" method appends a string to the end 
   of the character data of the node.
   
   Retrieve the character data from the second child 
   of the first employee.  The appendData(arg) method is
   called with arg=", Esquire".  The method should append 
   the specified data to the already existing character  
   data.  The new value return by the "getLength()" method
   should be 24.
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
	dom_string *childValue = NULL;
	int32_t childLength;
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
	const char *string1 = "name";
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
	const char *string2 = ", Esquire";
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

	exp = dom_characterdata_append_data((dom_characterdata *)child, dstring2);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_characterdata_append_data");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (child != NULL) { dom_node_unref(child); child = NULL; }
		if (nameNode != NULL) { dom_node_unref(nameNode); nameNode = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (childValue != NULL) {
		dom_string_unref(childValue);
		childValue = NULL;
	}
	exp = dom_characterdata_get_data((dom_characterdata *)child, &childValue);
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
childLength = dom_string_length(childValue);	assert(is_equals_int(24, childLength, false));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (childValue != NULL) { dom_string_unref(childValue); childValue = NULL; }
	if (child != NULL) { dom_node_unref(child); child = NULL; }
	if (nameNode != NULL) { dom_node_unref(nameNode); nameNode = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
