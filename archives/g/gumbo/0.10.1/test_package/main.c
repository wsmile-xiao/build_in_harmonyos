/* Consumer smoke for gumbo 0.10.1 — seven assertions: parse, root tag,
 * element/text counts (HTML5 void element <br> counts as an element),
 * body location, first-child tag, and attribute lookup. */
#include <gumbo.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s\n", (m)); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

static void walk(GumboNode *n, int *elems, int *texts) {
    if (n->type == GUMBO_NODE_ELEMENT) {
        (*elems)++;
        GumboVector *kids = &n->v.element.children;
        for (unsigned i = 0; i < kids->length; i++) walk((GumboNode *)kids->data[i], elems, texts);
    } else if (n->type == GUMBO_NODE_TEXT) {
        (*texts)++;
    }
}

int main(void) {
    const char *doc = "<html><head><title>t1</title></head><body><p id=\"a\">hello</p><br><p>world</p></body></html>";
    GumboOutput *out = gumbo_parse(doc);
    CHECK(out != NULL, "gumbo_parse");
    if (!out) {
        printf("FAIL: gumbo probe (%d failures)\n", failures);
        return 1;
    }
    CHECK(out->root != NULL && out->root->type == GUMBO_NODE_ELEMENT &&
          out->root->v.element.tag == GUMBO_TAG_HTML, "root is <html>");
    if (!out->root || out->root->type != GUMBO_NODE_ELEMENT) goto cleanup;

    int elems = 0, texts = 0;
    walk(out->root, &elems, &texts);
    CHECK(elems == 7, "seven elements (html/head/title/body/p/br/p)");
    CHECK(texts == 3, "three text nodes (title/hello/world)");

    GumboNode *body = 0;
    GumboVector *kids = &out->root->v.element.children;
    for (unsigned i = 0; i < kids->length; i++) {
        GumboNode *k = (GumboNode *)kids->data[i];
        if (k->type == GUMBO_NODE_ELEMENT && k->v.element.tag == GUMBO_TAG_BODY) { body = k; break; }
    }
    CHECK(body != NULL, "found <body>");
    if (body) {
        GumboVector *bk = &body->v.element.children;
        if (!bk->length || !bk->data || !bk->data[0]) {
            fprintf(stderr, "[FAIL] body has no first child\n");
            ++failures;
            goto cleanup;
        }
        GumboNode *p1 = (GumboNode *)bk->data[0];
        CHECK(p1->type == GUMBO_NODE_ELEMENT && p1->v.element.tag == GUMBO_TAG_P,
              "first child is <p>");
        if (p1->type != GUMBO_NODE_ELEMENT) goto cleanup;
        GumboAttribute *id = gumbo_get_attribute(&p1->v.element.attributes, "id");
        CHECK(id != NULL && strcmp(id->value, "a") == 0, "attribute id=a");
    }

cleanup:
    gumbo_destroy_output(&kGumboDefaultOptions, out);
    printf("%s: gumbo probe (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
