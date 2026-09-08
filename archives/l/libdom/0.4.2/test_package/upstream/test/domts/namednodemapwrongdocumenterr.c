/*
title: namednodemapWrongDocumentErr
creator: NIST
description: 

    The "setNamedItem(arg)" method raises a 
   WRONG_DOCUMENT_ERR DOMException if "arg" was created
   from a different document than the one that created
   the NamedNodeMap. 
   
   Create a NamedNodeMap object from the attributes of the
   last child of the third employee and attempt to add
   another Attr node to it that was created from a 
   different DOM document.  This should raise the desired
   exception.  This method uses the "createAttribute(name)"
   method from the Document interface.
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
	dom_document *doc1 = NULL;
	dom_document *doc2 = NULL;
	dom_nodelist *elementList = NULL;
	dom_node *testAddress = NULL;
	dom_namednodemap *attributes = NULL;
	dom_node *newAttribute = NULL;
	dom_node *setNode = NULL;
	const char *test1 = "staff.html";

	doc1 = load_html(test1, true);	if (doc1 == NULL) {
		const char *test2 = "staff.xml";

		doc1 = load_xml(test2, true);
		if (doc1 == NULL)
			return 1;
		}
	exp = dom_document_get_implementation((dom_document *) doc1, &doc_impl);
	if (exp != DOM_NO_ERR)
		return exp;
	const char *test3 = "staff.html";

	doc2 = load_html(test3, true);	if (doc2 == NULL) {
		const char *test4 = "staff.xml";

		doc2 = load_xml(test4, true);
		if (doc2 == NULL)
			return 1;
		}
	exp = dom_document_get_implementation((dom_document *) doc2, &doc_impl);
	if (exp != DOM_NO_ERR)
		return exp;
	const char *string1 = "address";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

		return exp;
	}

	if (elementList != NULL) {
		dom_nodelist_unref(elementList);
		elementList = NULL;
	}
	exp = dom_document_get_elements_by_tag_name((dom_document *)doc1, dstring1, &elementList);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_get_elements_by_tag_name");
		dom_string_unref(dstring1);
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

		return exp;
	}
	if (testAddress != NULL) {
		dom_node_unref(testAddress);
		testAddress = NULL;
	}
	exp = dom_nodelist_item((dom_nodelist *)elementList, 2, &testAddress);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_nodelist_item");
		dom_string_unref(dstring1);
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

		return exp;
	}
	const char *string2 = "newAttribute";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (testAddress != NULL) { dom_node_unref(testAddress); testAddress = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

		return exp;
	}

	if (newAttribute != NULL) {
		dom_node_unref(newAttribute);
		newAttribute = NULL;
	}
	exp = dom_document_create_attribute((dom_document *)doc2, dstring2, &newAttribute);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_attribute");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (testAddress != NULL) { dom_node_unref(testAddress); testAddress = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

		return exp;
	}
	if (attributes != NULL) {
		dom_namednodemap_unref(attributes);
		attributes = NULL;
	}
	exp = dom_node_get_attributes((dom_node *)testAddress, &attributes);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "attributes");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newAttribute != NULL) { dom_node_unref(newAttribute); newAttribute = NULL; }
		if (testAddress != NULL) { dom_node_unref(testAddress); testAddress = NULL; }
		if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
		if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
		if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }

		return exp;
	}
	if (setNode != NULL) {
		dom_node_unref(setNode);
		setNode = NULL;
	}
	exp = dom_namednodemap_set_named_item((dom_namednodemap *)attributes, newAttribute, &setNode);
assert(exp == 4);


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	if (setNode != NULL) { dom_node_unref(setNode); setNode = NULL; }
	if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
	if (newAttribute != NULL) { dom_node_unref(newAttribute); newAttribute = NULL; }
	if (testAddress != NULL) { dom_node_unref(testAddress); testAddress = NULL; }
	if (elementList != NULL) { dom_nodelist_unref(elementList); elementList = NULL; }
	if (doc2 != NULL) { dom_node_unref(doc2); doc2 = NULL; }
	if (doc1 != NULL) { dom_node_unref(doc1); doc1 = NULL; }


	printf("PASS");

	return 0;

}
