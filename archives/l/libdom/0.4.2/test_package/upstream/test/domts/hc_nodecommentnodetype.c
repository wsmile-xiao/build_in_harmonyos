/*
title: hc_nodeCommentNodeType
creator: Curt Arnold
description: 

    The "getNodeType()" method for a Comment Node
    returns the constant value 8.
    
    Retrieve the nodes from the document and check for
    a comment node and invoke the "getNodeType()" method.   This should   
    return 8. 
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
	dom_nodelist *testList = NULL;
	dom_node *commentNode = NULL;
	dom_string *commentNodeName = NULL;
	int32_t nodeType;
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
	if (testList != NULL) {
		dom_nodelist_unref(testList);
		testList = NULL;
	}
	exp = dom_node_get_child_nodes((dom_node *)doc, &testList);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "childNodes");
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
unsigned int iterator1 = 0;foreach_initialise_domnodelist(testList, &iterator1);
while(get_next_domnodelist(testList, &iterator1, &commentNode)) {
	if (commentNodeName != NULL) {
		dom_string_unref(commentNodeName);
		commentNodeName = NULL;
	}
	exp = dom_node_get_node_name((dom_node *)commentNode, &commentNodeName);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeName");
		if (commentNode != NULL) { dom_node_unref(commentNode); commentNode = NULL; }
		if (testList != NULL) { dom_nodelist_unref(testList); testList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	if(is_equals_string("#comment", commentNodeName, false)) {
	exp = dom_node_get_node_type((dom_node *)commentNode, &nodeType);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeType");
		if (commentNodeName != NULL) { dom_string_unref(commentNodeName); commentNodeName = NULL; }
		if (commentNode != NULL) { dom_node_unref(commentNode); commentNode = NULL; }
		if (testList != NULL) { dom_nodelist_unref(testList); testList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_int(8, nodeType, false));
}
if (commentNode != NULL) {
    dom_node_unref(commentNode);
    commentNode = NULL;
}
}
	const char *string1 = "This is a comment";
	dom_string *dstring1;
	exp = dom_string_create((const uint8_t *)string1,
			strlen(string1), &dstring1);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Can't create DOMString\n");
		if (commentNodeName != NULL) { dom_string_unref(commentNodeName); commentNodeName = NULL; }
		if (commentNode != NULL) { dom_node_unref(commentNode); commentNode = NULL; }
		if (testList != NULL) { dom_nodelist_unref(testList); testList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}

	if (commentNode != NULL) {
		dom_node_unref(commentNode);
		commentNode = NULL;
	}
	exp = dom_document_create_comment((dom_document *)doc, dstring1, &commentNode);
	if (exp != DOM_NO_ERR) {
	fprintf(stderr, "Exception raised from %s\n", "dom_document_create_comment");
		dom_string_unref(dstring1);
		if (commentNodeName != NULL) { dom_string_unref(commentNodeName); commentNodeName = NULL; }
		if (commentNode != NULL) { dom_node_unref(commentNode); commentNode = NULL; }
		if (testList != NULL) { dom_nodelist_unref(testList); testList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	exp = dom_node_get_node_type((dom_node *)commentNode, &nodeType);
	if (exp != DOM_NO_ERR) {
		fprintf(stderr, "Exception raised when fetch attribute %s", "nodeType");
		dom_string_unref(dstring1);
		if (commentNodeName != NULL) { dom_string_unref(commentNodeName); commentNodeName = NULL; }
		if (commentNode != NULL) { dom_node_unref(commentNode); commentNode = NULL; }
		if (testList != NULL) { dom_nodelist_unref(testList); testList = NULL; }
		if (doc != NULL) { dom_node_unref(doc); doc = NULL; }

		return exp;
	}
	assert(is_equals_int(8, nodeType, false));


	dom_string_unref(dstring1);
	if (commentNodeName != NULL) { dom_string_unref(commentNodeName); commentNodeName = NULL; }
	if (commentNode != NULL) { dom_node_unref(commentNode); commentNode = NULL; }
	if (testList != NULL) { dom_nodelist_unref(testList); testList = NULL; }
	if (doc != NULL) { dom_node_unref(doc); doc = NULL; }


	printf("PASS");

	return 0;

}
