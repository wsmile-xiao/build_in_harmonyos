#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lexbor/html/html.h>
#include <lexbor/dom/dom.h>

/* R34: test_package must really exercise the packaged library.
 * Parse a small HTML fragment and verify the resulting DOM tree. */
int main(void) {
    lxb_html_document_t *document;
    lxb_dom_element_t *body;
    lxb_dom_element_t *div;
    const lxb_char_t *html = (const lxb_char_t *)"<html><body><div id='t'>hello lexbor</div></body></html>";
    size_t html_len = strlen((const char *)html);

    document = lxb_html_document_create();
    if (document == NULL) {
        fprintf(stderr, "FAIL: lxb_html_document_create() == NULL\n");
        return 1;
    }

    lxb_html_document_parse(document, html, html_len);

    body = lxb_dom_interface_element(lxb_html_document_body_element(document));
    if (body == NULL) {
        fprintf(stderr, "FAIL: no <body> element parsed\n");
        lxb_html_document_destroy(document);
        return 1;
    }

    div = lxb_dom_element_by_id(body,
                                (const lxb_char_t *)"t", 1);
    if (div == NULL) {
        fprintf(stderr, "FAIL: element #t not found\n");
        lxb_html_document_destroy(document);
        return 1;
    }

    printf("lexbor 3.0.0: parse + element_by_id OK\n");
    lxb_html_document_destroy(document);
    return 0;
}
