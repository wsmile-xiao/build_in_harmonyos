#include <string.h>
#include <talloc.h>

int main(void) {
    TALLOC_CTX *root = talloc_new(NULL);
    char *child;
    if (root == NULL) return 1;
    child = talloc_strdup(root, "HarmonyOS");
    if (child == NULL || strcmp(child, "HarmonyOS") != 0) return 2;
    if (talloc_total_blocks(root) < 2) return 3;
    talloc_free(root);
    return 0;
}
