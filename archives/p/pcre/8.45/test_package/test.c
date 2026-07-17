#include <pcre.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *error;
    int erroffset;
    int ovector[30];

    /* Compile a simple regex pattern */
    pcre *re = pcre_compile("^Hello (\\w+)$", 0, &error, &erroffset, NULL);
    if (re == NULL) {
        printf("pcre_compile failed at offset %d: %s\n", erroffset, error);
        return 1;
    }

    /* Test matching */
    const char *input = "Hello World";
    int rc = pcre_exec(re, NULL, input, (int)strlen(input), 0, 0, ovector, 30);
    if (rc >= 0) {
        printf("pcre test: matched successfully (rc=%d)\n", rc);
    } else {
        printf("pcre test: no match (rc=%d)\n", rc);
        pcre_free(re);
        return 1;
    }

    /* Extract captured group */
    const char *substr = NULL;
    int ret = pcre_get_substring(input, ovector, rc, 1, &substr);
    if (ret >= 0 && substr) {
        printf("pcre test: captured group = '%s'\n", substr);
        pcre_free_substring(substr);
    }

    /* Verify version */
    const char *ver = pcre_version();
    printf("pcre version: %s\n", ver);

    pcre_free(re);
    return 0;
}
