#include <stdio.h>
#include <string.h>
#include "exSID.h"

int main(void)
{
    void *handle;

    if (EXSID_MAJOR_VERSION != 2 || EXSID_MINOR_VERSION != 1 || EXSID_REVISION != 0) {
        fprintf(stderr, "unexpected libexsid version macros\n");
        return 1;
    }
    if (!EXSID_VERSION_CHECK(2, 1) || EXSID_VERSION_CHECK(3, 0)) {
        fprintf(stderr, "version compatibility macro failed\n");
        return 2;
    }
    if (exSID_error_str(NULL) != NULL) {
        fprintf(stderr, "NULL handle should have no error string\n");
        return 3;
    }
    handle = exSID_new();
    if (handle == NULL) {
        fprintf(stderr, "exSID_new allocation failed\n");
        return 4;
    }
    if (exSID_error_str(handle) == NULL || exSID_error_str(handle)[0] != '\0') {
        fprintf(stderr, "new handle should start with an empty error string\n");
        exSID_free(handle);
        return 5;
    }
    exSID_free(handle);
    exSID_free(NULL);

    puts("libexsid consumer API checks passed");
    return 0;
}
