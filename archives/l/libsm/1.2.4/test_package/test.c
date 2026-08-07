#include <X11/SM/SMlib.h>
#include <X11/ICE/ICElib.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void test_error_handler(SmcConn smcConn, Bool swap,
                               int offendingMinorOpcode,
                               unsigned long offendingSequence,
                               int errorClass, int severity,
                               SmPointer values) {
    (void)smcConn;
    (void)swap;
    (void)offendingMinorOpcode;
    (void)offendingSequence;
    (void)errorClass;
    (void)severity;
    (void)values;
}

int main(void) {
    SmcErrorHandler previous_handler;

    /* Test SmcSetErrorHandler: set and restore */
    previous_handler = SmcSetErrorHandler(test_error_handler);
    if (SmcSetErrorHandler(previous_handler) != test_error_handler) {
        fprintf(stderr, "SmcSetErrorHandler did not return the active handler\n");
        return 1;
    }

    /* Test SmFreeProperty with properly heap-allocated data */
    SmProp *prop = malloc(sizeof(SmProp));
    if (prop == NULL) {
        fprintf(stderr, "malloc SmProp failed\n");
        return 2;
    }
    SmPropValue *vals = malloc(sizeof(SmPropValue));
    if (vals == NULL) {
        fprintf(stderr, "malloc SmPropValue failed\n");
        free(prop);
        return 3;
    }
    prop->name = strdup("SmProgram");
    prop->type = strdup("STRING");
    prop->num_vals = 1;
    prop->vals = vals;
    vals->length = 5;
    vals->value = malloc(5);
    if (vals->value == NULL) {
        fprintf(stderr, "malloc value failed\n");
        free(vals);
        free(prop->name);
        free(prop->type);
        free(prop);
        return 4;
    }
    memcpy(vals->value, "test", 5);
    SmFreeProperty(prop);

    /* Test SmFreeReasons with properly heap-allocated data */
    char **reasons = malloc(2 * sizeof(char *));
    if (reasons == NULL) {
        fprintf(stderr, "malloc reasons failed\n");
        return 5;
    }
    reasons[0] = strdup("reason1");
    reasons[1] = strdup("reason2");
    SmFreeReasons(2, reasons);

    puts("LIBSM_TEST api_contract PASS");
    return 0;
}
