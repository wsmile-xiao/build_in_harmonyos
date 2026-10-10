#include <string.h>
#include <stdio.h>

/* Deliberately insecure sample used by the rats consumer test:
 * it exercises unbounded strcpy/strcat and a non-constant sprintf so that
 * the packaged `rats` binary (with its C vulnerability database + expat)
 * must report at least one finding. */
int main(int argc, char **argv) {
    char buf[16];
    char *src = argv[1];
    strcpy(buf, src);                 /* unbounded copy */
    strcat(buf, "x");                 /* unbounded append */
    sprintf(buf, "%s", src);          /* non-bounded format */
    printf("%s\n", buf);
    return 0;
}
