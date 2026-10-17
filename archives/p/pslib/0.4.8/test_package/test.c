#include <libps/pslib.h>

#include <stdio.h>
#include <string.h>

static int contains_bytes(const char *haystack, long haystack_size,
                          const char *needle) {
    size_t needle_size = strlen(needle);
    long i;
    if (!haystack || haystack_size < 0 || (size_t)haystack_size < needle_size)
        return 0;
    for (i = 0; (size_t)i + needle_size <= (size_t)haystack_size; ++i) {
        if (memcmp(haystack + i, needle, needle_size) == 0)
            return 1;
    }
    return 0;
}

int main(void) {
    PSDoc *doc;
    const char *buffer;
    long size = 0;
    int result = 1;

    if (PS_get_majorversion() != 0 || PS_get_minorversion() != 4 ||
        PS_get_subminorversion() != 8)
        return 2;
    doc = PS_new();
    if (!doc)
        return 3;
    if (PS_open_mem(doc, NULL) != 0)
        goto done;
    PS_begin_page(doc, 72.0f, 72.0f);
    PS_end_page(doc);
    PS_close(doc);
    buffer = PS_get_buffer(doc, &size);
    if (contains_bytes(buffer, size, "%!PS-Adobe") &&
        contains_bytes(buffer, size, "%%Pages: 1") &&
        contains_bytes(buffer, size, "%%EOF")) {
        puts("pslib memory-document consumer: PASS");
        result = 0;
    }
done:
    PS_delete(doc);
    return result;
}
