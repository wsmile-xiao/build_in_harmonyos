/* Consumer test for json-build 1.2.0 (header-only).
 * Uses only the installed public header json-build.h and the public
 * jsonb_* serializer API; verifies the produced JSON output string.
 */
#include <stdio.h>
#include <string.h>

#include "json-build.h"

int main(void)
{
    jsonb b;
    char buf[1024];

    jsonb_init(&b);
    jsonb_object(&b, buf, sizeof(buf));
    {
        jsonb_key(&b, buf, sizeof(buf), "foo", strlen("foo"));
        jsonb_array(&b, buf, sizeof(buf));
        {
            jsonb_number(&b, buf, sizeof(buf), 1);
            jsonb_string(&b, buf, sizeof(buf), "hi", 2);
            jsonb_bool(&b, buf, sizeof(buf), 0);
            jsonb_null(&b, buf, sizeof(buf));
            jsonb_array_pop(&b, buf, sizeof(buf));
        }
        jsonb_object_pop(&b, buf, sizeof(buf));
    }

    if (strcmp(buf, "{\"foo\":[1,\"hi\",false,null]}") != 0) {
        fprintf(stderr, "FAIL: unexpected JSON output: %s\n", buf);
        return 1;
    }
    printf("consumer test OK: %s\n", buf);
    return 0;
}
