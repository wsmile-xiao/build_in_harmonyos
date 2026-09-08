/*
title: elementGetElementsByTagNamesSpecialValue
creator: NIST
description: 

The "getElementsByTagName(name)" method may use the
special value "*" to match all tags in the element
tree.

Create a NodeList of all the descendant elements
of the last employee by using the special value "*".
The method should return all the descendant children(6)
in the order the children were encountered.
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
	dom_element *lastEmployee = NULL;
	dom_nodelist *lastempList = NULL;
	dom_node *child = NULL;
	dom_string *childName = NULL;
	list *result = NULL;
	list *expectedResult = NULL;
const char *expectedResultArray[] = { "employeeId", "name", "position", "salary", "gender", "address"};
expectedResult = list_new(STRING);
result = list_new(DOM_STRING);
list_add(expectedResult, *(char **)(expectedResultArray + 0));
list_add(expectedResult, *(char **)(expectedResultArray + 1));
list_add(expectedResult, *(char **)(expectedResultArray + 2));
list_add(expectedResult, *(char **)(expectedResultArray + 3));
list_add(expectedResult, *(char **)(expectedResultArray + 4));
list_add(expectedResult, *(char **)(expectedResultArray + 5));
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
	const char *string1 = "employee";
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
	if (lastEmployee != NULL) {
		dom_node_unref(lastEmployee);
		lastEmployee = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 4, &lastEmployee);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "*";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (lastEmployee != NULL) { dom_node_unref(lastEmployee); lastEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (lastempList != NULL) {
		dom_nodelist_unref(lastempList);
		lastempList = NULL;
	}
	exp = dom_element_get_elements_by_tag_name((dom_element *)lastEmployee, dstring2, &lastempList);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_get_elements_by_tag_name");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (lastEmployee != NULL) { dom_node_unref(lastEmployee); lastEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
unsigned int iterator1 = 0;foreach_initialise_domnodelist(lastempList, &iterator1);
while(get_next_domnodelist(lastempList, &iterator1, &child)) {
	if (childName != NULL) {
		dom_string_unref(childName);
		childName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)child, &childName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (child != NULL) { dom_node_unref(child); child = NULL; }
		if (lastempList != NULL) { dom_nodelist_unref(lastempList); lastempList = NULL; }
		if (lastEmployee != NULL) { dom_node_unref(lastEmployee); lastEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
list_add(result, childName);
if (child != NULL) {
    dom_node_unref(child);
    child = NULL;
}
}
	assert(is_equals_list(expectedResult, result, false));


	if (expectedResult != NULL)
		list_destroy(expectedResult);
	if (result != NULL)
		list_destroy(result);
	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (childName != NULL) { dom_string_unref(childName); childName = NULL; }
	if (child != NULL) { dom_node_unref(child); child = NULL; }
	if (lastempList != NULL) { dom_nodelist_unref(lastempList); lastempList = NULL; }
	if (lastEmployee != NULL) { dom_node_unref(lastEmployee); lastEmployee = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
