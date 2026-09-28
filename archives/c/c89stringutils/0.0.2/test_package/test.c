#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c89stringutils_string_extras.h"

int main(void) {
    /* strnstr: 在限定长度内查找子串 */
    const char *hay = "hello c89stringutils world";
    char *found = strnstr(hay, "c89stringutils", strlen(hay));
    if (!found) {
        printf("FAIL: strnstr not found\n");
        return 1;
    }

    /* strcasecmp: 大小写不敏感比较 */
    if (strcasecmp("HarmonyOS", "harmonyos") != 0) {
        printf("FAIL: strcasecmp mismatch\n");
        return 1;
    }

    /* asprintf: 动态格式化 */
    char *buf = NULL;
    if (asprintf(&buf, "%s-%d", "c89stringutils", 2) < 0 || !buf) {
        printf("FAIL: asprintf\n");
        return 1;
    }
    int ok = (strcmp(buf, "c89stringutils-2") == 0);
    free(buf);
    if (!ok) {
        printf("FAIL: asprintf content\n");
        return 1;
    }

    printf("test c89stringutils 0.0.2: OK (strnstr/strcasecmp/asprintf passed)\n");
    return 0;
}
