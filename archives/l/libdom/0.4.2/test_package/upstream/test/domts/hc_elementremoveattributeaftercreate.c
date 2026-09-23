/*
title: hc_elementRemoveAttributeAfterCreate
creator: Curt Arnold
description: 

    The "removeAttributeNode(oldAttr)" method removes the 
   specified attribute. 
   
   Retrieve the last child of the third employee, add a
   new "lang" attribute to it and then try to remove it. 
   To verify that the node was removed use the
   "getNamedItem(name)" method from the NamedNodeMap
   interface.  It also uses the "getAttributes()" method
   from the Node interface.
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
	dom_element *testEmployee = NULL;
	dom_attr *newAttribute = NULL;
	dom_namednodemap *attributes = NULL;
	dom_attr *districtAttr = NULL;
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
	const char *string1 = "acronym";
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
	if (testEmployee != NULL) {
		dom_node_unref(testEmployee);
		testEmployee = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 2, &testEmployee);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "lang";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (newAttribute != NULL) {
		dom_node_unref(newAttribute);
		newAttribute = NULL;
	}
	exp = dom_document_create_attribute((dom_document *)doc, dstring2, &newAttribute);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_attribute");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (districtAttr != NULL) {
		dom_node_unref(districtAttr);
		districtAttr = NULL;
	}
	exp = dom_element_set_attribute_node((dom_element *)testEmployee, newAttribute, &districtAttr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_set_attribute_node");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newAttribute != NULL) { dom_node_unref(newAttribute); newAttribute = NULL; }
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (districtAttr != NULL) {
		dom_node_unref(districtAttr);
		districtAttr = NULL;
	}
	exp = dom_element_remove_attribute_node((dom_element *)testEmployee, newAttribute, &districtAttr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_remove_attribute_node");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (districtAttr != NULL) { dom_node_unref(districtAttr); districtAttr = NULL; }
		if (newAttribute != NULL) { dom_node_unref(newAttribute); newAttribute = NULL; }
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (attributes != NULL) {
		dom_namednodemap_unref(attributes);
		attributes = NULL;
	}
	exp = dom_node_get_attributes((dom_node *)testEmployee, &attributes);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "attributes");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (districtAttr != NULL) { dom_node_unref(districtAttr); districtAttr = NULL; }
		if (newAttribute != NULL) { dom_node_unref(newAttribute); newAttribute = NULL; }
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
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
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (districtAttr != NULL) { dom_node_unref(districtAttr); districtAttr = NULL; }
		if (newAttribute != NULL) { dom_node_unref(newAttribute); newAttribute = NULL; }
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (districtAttr != NULL) {
		dom_node_unref(districtAttr);
		districtAttr = NULL;
	}
	exp = dom_namednodemap_get_named_item((dom_namednodemap *)attributes, dstring3, &districtAttr);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_namednodemap_get_named_item");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (districtAttr != NULL) { dom_node_unref(districtAttr); districtAttr = NULL; }
		if (newAttribute != NULL) { dom_node_unref(newAttribute); newAttribute = NULL; }
		if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_null(districtAttr));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	dom_string_unref(dstring3);
	if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
	if (districtAttr != NULL) { dom_node_unref(districtAttr); districtAttr = NULL; }
	if (newAttribute != NULL) { dom_node_unref(newAttribute); newAttribute = NULL; }
	if (testEmployee != NULL) { dom_node_unref(testEmployee); testEmployee = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
