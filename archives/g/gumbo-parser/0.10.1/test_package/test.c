#include <gumbo.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    const char* html = "<!doctype html><html><body><h1>HarmonyOS</h1></body></html>";
    GumboOutput* output = gumbo_parse(html);
    if (output == NULL || output->root == NULL ||
        output->root->type != GUMBO_NODE_ELEMENT ||
        output->root->v.element.tag != GUMBO_TAG_HTML) {
        fprintf(stderr, "gumbo_parse did not produce an HTML root\n");
        if (output != NULL) {
            gumbo_destroy_output(&kGumboDefaultOptions, output);
        }
        return 1;
    }

    GumboVector* html_children = &output->root->v.element.children;
    if (html_children->length != 2) {
        fprintf(stderr, "expected head and body nodes\n");
        gumbo_destroy_output(&kGumboDefaultOptions, output);
        return 2;
    }

    GumboNode* body = html_children->data[1];
    if (body->type != GUMBO_NODE_ELEMENT || body->v.element.tag != GUMBO_TAG_BODY ||
        body->v.element.children.length != 1) {
        fprintf(stderr, "expected a body with one child\n");
        gumbo_destroy_output(&kGumboDefaultOptions, output);
        return 3;
    }

    GumboNode* heading = body->v.element.children.data[0];
    if (heading->type != GUMBO_NODE_ELEMENT || heading->v.element.tag != GUMBO_TAG_H1 ||
        heading->v.element.children.length != 1) {
        fprintf(stderr, "expected an h1 element\n");
        gumbo_destroy_output(&kGumboDefaultOptions, output);
        return 4;
    }

    GumboNode* text = heading->v.element.children.data[0];
    if (text->type != GUMBO_NODE_TEXT || strcmp(text->v.text.text, "HarmonyOS") != 0) {
        fprintf(stderr, "unexpected h1 text\n");
        gumbo_destroy_output(&kGumboDefaultOptions, output);
        return 5;
    }

    gumbo_destroy_output(&kGumboDefaultOptions, output);
    return 0;
}