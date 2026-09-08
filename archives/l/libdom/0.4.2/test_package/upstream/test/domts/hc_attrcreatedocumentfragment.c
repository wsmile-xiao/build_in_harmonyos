/*
title: hc_attrcreatedocumentfragment
creator: Curt Arnold
description: 

  Create a new DocumentFragment and add a newly created Element node(with one attribute).  
  Once the element is added, its attribute should be available as an attribute associated 
  with an Element within a DocumentFragment.
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
	dom_document_fragment *docFragment = NULL;
	dom_element *newOne = NULL;
	dom_node *domesticNode = NULL;
	dom_namednodemap *attributes = NULL;
	dom_attr *attribute = NULL;
	dom_string *attrName = NULL;
	dom_node *appendedChild = NULL;
	int32_t langAttrCount = 0;
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
	const char *string1 = "html";
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
	const char *string2 = "lang";
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

	const char *string3 = "EN";
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
	if (attributes != NULL) {
		dom_namednodemap_unref(attributes);
		attributes = NULL;
	}
	exp = dom_node_get_attributes((dom_node *)domesticNode, &attributes);
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
unsigned int iterator1 = 0;foreach_initialise_domnamednodemap(attributes, &iterator1);
while(get_next_domnamednodemap(attributes, &iterator1, &attribute)) {
	if (attrName != NULL) {
		dom_string_unref(attrName);
		attrName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)attribute, &attrName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		dom_string_unref(dstring1);
		dom_string_unref(dstring2);
		dom_string_unref(dstring3);
		if (attribute != NULL) { dom_node_unref(attribute); attribute = NULL; }
		if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
		if (domesticNode != NULL) { dom_node_unref(domesticNode); domesticNode = NULL; }
		if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
		if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
		if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if(is_equals_string("lang", attrName, true)) {
langAttrCount += 1;
}
if (attribute != NULL) {
    dom_node_unref(attribute);
    attribute = NULL;
}
}
	assert(is_equals_int(1, langAttrCount, false));


	dom_string_unref(dstring1);
	dom_string_unref(dstring2);
	dom_string_unref(dstring3);
	if (attrName != NULL) { dom_string_unref(attrName); attrName = NULL; }
	if (attribute != NULL) { dom_node_unref(attribute); attribute = NULL; }
	if (attributes != NULL) { dom_namednodemap_unref(attributes); attributes = NULL; }
	if (domesticNode != NULL) { dom_node_unref(domesticNode); domesticNode = NULL; }
	if (appendedChild != NULL) { dom_node_unref(appendedChild); appendedChild = NULL; }
	if (newOne != NULL) { dom_node_unref(newOne); newOne = NULL; }
	if (docFragment != NULL) { dom_node_unref(docFragment); docFragment = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
