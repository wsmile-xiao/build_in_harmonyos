#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <parse.h>
#include <object.h>

/* Consumer test: parse a JSON document through the installed public API
 * (parseJSON -> Object -> object_toString -> object_free) and verify the
 * round-trip output matches expectations. R34: real API usage, no print-only. */
int main(void) {
    const char *json = "{\"arr\":[1,\"value\",-1.23e1,[{\"sub\":1}]],\"name\":\"希望666\"}";
    char *buf = (char *)calloc(strlen(json) + 1, sizeof(char));
    Object *obj = NULL;
    int flag = 1;
    int status = 0;
    char *out = NULL;
    int ok = 1;

    if (!buf) return 2;
    strcpy(buf, json);

    status = parseJSON(buf, &flag, &obj);
    if (status <= 0 || !obj) {
        fprintf(stderr, "parseJSON failed: status=%d\n", status);
        free(buf);
        return 1;
    }

    out = object_toString(obj);
    if (!out) {
        fprintf(stderr, "object_toString returned NULL\n");
        object_free(obj);
        free(buf);
        return 1;
    }

    printf("parsed_len=%d\n%s\n", status, out);

    /* verify round-trip keeps the dict key and array members */
    if (strstr(out, "\"arr\"") == NULL) ok = 0;
    if (strstr(out, "\"name\":\"希望666\"") == NULL) ok = 0;
    if (strstr(out, "\"value\"") == NULL) ok = 0;

    free(out);
    object_free(obj);
    free(buf);

    if (!ok) {
        fprintf(stderr, "round-trip verification failed\n");
        return 1;
    }
    printf("jsonparse-cpp consumer test: OK\n");
    return 0;
}
