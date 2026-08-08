#include <X11/SM/SMlib.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *duplicate_text(const char *text) {
    size_t length = strlen(text) + 1;
    char *copy = malloc(length);
    if (copy != NULL) {
        memcpy(copy, text, length);
    }
    return copy;
}

int main(void) {
    static const char first_value[] = "first";
    static const char second_value[] = "second";
    SmProp *property = calloc(1, sizeof(*property));
    char **reasons = calloc(2, sizeof(*reasons));

    if (property == NULL || reasons == NULL) {
        free(property);
        free(reasons);
        return 1;
    }

    property->name = duplicate_text(SmProgram);
    property->type = duplicate_text(SmLISTofARRAY8);
    property->num_vals = 2;
    property->vals = calloc(2, sizeof(*property->vals));
    reasons[0] = duplicate_text("normal shutdown");
    reasons[1] = duplicate_text("session replaced");
    if (property->name == NULL || property->type == NULL ||
        property->vals == NULL || reasons[0] == NULL || reasons[1] == NULL) {
        SmFreeProperty(property);
        SmFreeReasons(2, reasons);
        return 2;
    }

    property->vals[0].length = (int)(sizeof(first_value) - 1);
    property->vals[0].value = duplicate_text(first_value);
    property->vals[1].length = (int)(sizeof(second_value) - 1);
    property->vals[1].value = duplicate_text(second_value);
    if (property->vals[0].value == NULL || property->vals[1].value == NULL) {
        SmFreeProperty(property);
        SmFreeReasons(2, reasons);
        return 3;
    }

    SmFreeProperty(property);
    SmFreeReasons(2, reasons);
    SmFreeProperty(NULL);
    SmFreeReasons(0, NULL);
    puts("LIBSM_TEST memory_contract PASS");
    return 0;
}
