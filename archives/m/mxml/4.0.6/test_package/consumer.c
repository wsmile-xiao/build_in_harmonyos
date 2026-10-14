#include <mxml.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    mxml_node_t *tree = mxmlLoadString(NULL, NULL,
                                      "<root><item value=\"ok\"/></root>");
    if (!tree) {
        fputs("mxmlLoadString failed\n", stderr);
        return 1;
    }

    mxml_node_t *item = mxmlFindElement(tree, tree, "item", "value", "ok",
                                       MXML_DESCEND_ALL);
    if (!item) {
        fputs("mxmlFindElement failed\n", stderr);
        mxmlDelete(tree);
        return 2;
    }

    char *saved = mxmlSaveAllocString(tree, NULL);
    if (!saved || !strstr(saved, "value=\"ok\"")) {
        fputs("mxmlSaveAllocString failed\n", stderr);
        free(saved);
        mxmlDelete(tree);
        return 3;
    }

    free(saved);
    mxmlDelete(tree);
    puts("Mini-XML installed API consumer passed");
    return 0;
}
