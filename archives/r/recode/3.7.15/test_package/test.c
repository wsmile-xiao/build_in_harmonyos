#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <recode.h>

int main(void)
{
    RECODE_OUTER outer = recode_new_outer(RECODE_AUTO_ABORT_FLAG);
    RECODE_REQUEST request;
    char *converted = NULL;
    size_t length = 0;
    size_t allocated = 0;
    int result = 1;

    if (!outer)
        return 1;
    request = recode_new_request(outer);
    if (request && recode_scan_request(request, "UTF-8..ASCII") &&
        recode_string_to_buffer(request, "recode", &converted, &length,
                                &allocated) &&
        length == 6 && converted && memcmp(converted, "recode", 6) == 0)
        result = 0;
    free(converted);
    if (request)
        recode_delete_request(request);
    recode_delete_outer(outer);
    puts(result == 0 ? "recode consumer: PASS" : "recode consumer: FAIL");
    return result;
}
