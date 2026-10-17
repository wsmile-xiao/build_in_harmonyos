#include <libcob.h>
#include <stdio.h>
#include <string.h>

static int test_memory_api(void) {
    const char expected[] = "libcob API: OK";
    char *buffer = cob_malloc(sizeof(expected));
    if (!buffer) {
        fprintf(stderr, "test_memory_api: cob_malloc returned NULL\n");
        return 1;
    }

    memcpy(buffer, expected, sizeof(expected));
    puts(buffer);
    cob_free(buffer);
    return 0;
}

static int test_field_string_bounds(void) {
    static const cob_field_attr attr = {
        COB_TYPE_ALPHANUMERIC, 0, 0, 0, NULL
    };
    unsigned char source[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    cob_field field = {sizeof(source) - 1, source, &attr};
    struct {
        char buffer[8];
        unsigned char sentinel[64];
    } output;
    size_t i;

    memset(&output, 0xA5, sizeof(output));
    cob_get_field_str(&field, output.buffer, sizeof(output.buffer));

    for (i = 0; i < sizeof(output.sentinel); ++i) {
        if (output.sentinel[i] != 0xA5) {
            return 1;
        }
    }
    if (memcmp(output.buffer, "ABCDEFG", 7) != 0 || output.buffer[7] != '\0') {
        return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    cob_module *module = NULL;
    cob_global *global = NULL;
    int result;

    cob_init(argc, argv);
    cob_module_enter(&module, &global, 0);
    result = test_memory_api() || test_field_string_bounds();
    cob_module_leave(module);
    cob_tidy();
    return result;
}
