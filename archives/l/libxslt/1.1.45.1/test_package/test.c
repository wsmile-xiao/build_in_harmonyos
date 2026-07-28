#include <libxslt/xsltconfig.h>
#include <libxslt/xslt.h>
#include <stdio.h>

int main(void) {
    if (LIBXSLT_VERSION < 10145) {
        fprintf(stderr, "unexpected libxslt version: %d\n", LIBXSLT_VERSION);
        return 1;
    }
    if (xsltLibxsltVersion < 10145) {
        fprintf(
            stderr,
            "unexpected libxslt runtime version: %d\n",
            xsltLibxsltVersion
        );
        return 1;
    }
    xsltInit();
    xsltCleanupGlobals();
    printf("libxslt link probe ok: %d\n", xsltLibxsltVersion);
    return 0;
}
