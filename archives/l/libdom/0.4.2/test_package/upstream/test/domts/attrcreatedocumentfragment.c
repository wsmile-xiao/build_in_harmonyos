/*
title: attrCreateDocumentFragment
creator: NIST
description: 

    Attr nodes may be associated with Element nodes contained within a DocumentFragment.
  Create a new DocumentFragment and add a newly created Element node(with one attribute).  
  Once the element is added, its attribute should be available as an attribute associated 
  with an Element within a DocumentFragment.
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
	dom_document_fragment *docFragment = NULL;
	dom_element *newOne = NULL;
	dom_node *domesticNode = NULL;
	dom_namednodemap *domesticAttr = NULL;
	dom_attr *attrs = NULL;
	dom_string *attrName = NULL;
	dom_node *appendedChild = NULL;
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
	if (docFragment != NULL) {
		dom_node_unref(docFragment);
		docFragment = NULL;
	}
	exp = dom_document_create_document_fragment((dom_document *)doc, &docFragment);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_document_fragment");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string1 = "newElement";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (newOne != NULL) {
		dom_node_unref(newOne);
		newOne = NULL;
	}
	exp = dom_document_create_element((dom_document *)doc, dstring1, &newOne);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_element");
		dom_string_unref(dstring1);
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	const char *string2 = "newdomestic";
	dom_string *dstring2;
	exp = dom_string_create((const uint8_t *)string2,
			strlen(string2), &dstring2);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	const char *string3 = "Yes";
	dom_string *dstring3;
	exp = dom_string_create((const uint8_t *)string3,
			strlen(string3), &dstring3);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	exp = dom_element_set_attribute((dom_element *)newOne, dstring2, dstring3);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_element_set_attribute");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (appendedChild != NULL) {
		dom_node_unref(appendedChild);
		appendedChild = NULL;
	}
	exp = dom_node_append_child((dom_node *)docFragment, newOne, &appendedChild);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_node_append_child");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (domesticNode != NULL) {
		dom_node_unref(domesticNode);
		domesticNode = NULL;
	}
	exp = dom_node_get_first_child((dom_node *)docFragment, &domesticNode);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "firstChild");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
		if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (domesticAttr != NULL) {
		dom_namednodemap_unref(domesticAttr);
		domesticAttr = NULL;
	}
	exp = dom_node_get_attributes((dom_node *)domesticNode, &domesticAttr);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "attributes");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (domesticNode != NULL) { dom_node_unref(domesticNode); domesticNode = NULL; }
		if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
		if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (attrs != NULL) {
		dom_node_unref(attrs);
		attrs = NULL;
	}
	exp = dom_namednodemap_item((dom_namednodemap *)domesticAttr, 0, &attrs);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_namednodemap_item");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (domesticAttr != NULL) { dom_namednodemap_unref(domesticAttr); domesticAttr = NULL; }
		if (domesticNode != NULL) { dom_node_unref(domesticNode); domesticNode = NULL; }
		if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
		if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if (attrName != NULL) {
		dom_string_unref(attrName);
		attrName = NULL;
	}
	exp = dom_attr_get_name((dom_attr *)attrs, &attrName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "name");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (attrs != NULL) { dom_node_unref(attrs); attrs = NULL; }
		if (domesticAttr != NULL) { dom_namednodemap_unref(domesticAttr); domesticAttr = NULL; }
		if (domesticNode != NULL) { dom_node_unref(domesticNode); domesticNode = NULL; }
		if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
		if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_string("newdomestic", attrName, false));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	dom_string_unref(dstring3);
	if (attrName != NULL) { dom_string_unref(attrName); attrName = NULL; }
	if (attrs != NULL) { dom_node_unref(attrs); attrs = NULL; }
	if (domesticAttr != NULL) { dom_namednodemap_unref(domesticAttr); domesticAttr = NULL; }
	if (domesticNode != NULL) { dom_node_unref(domesticNode); domesticNode = NULL; }
	if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
	if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
	if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
