#include <lo/lo.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    lo_message message = lo_message_new();
    lo_message decoded = NULL;
    void *wire = NULL;
    size_t wire_size = 0;
    int result = -1;
    int rc = 1;

    if (!message || lo_message_add_int32(message, INT32_C(42)) != 0)
        goto done;
    wire = lo_message_serialise(message, "/harmony/probe", NULL, &wire_size);
    if (!wire || wire_size == 0)
        goto done;
    decoded = lo_message_deserialise(wire, wire_size, &result);
    if (!decoded || lo_message_get_argc(decoded) != 1 ||
        strcmp(lo_message_get_types(decoded), "i") != 0 ||
        lo_message_get_argv(decoded)[0]->i != 42)
        goto done;

    puts("LIBLO_CONSUMER_1_OF_1_PASS");
    rc = 0;
done:
    lo_message_free(decoded);
    lo_message_free(message);
    free(wire);
    return rc;
}
