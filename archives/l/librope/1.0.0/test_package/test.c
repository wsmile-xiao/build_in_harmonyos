/* test_package consumer test — exercises the real librope rope API (R34).
 *
 * Inserts a UTF-8 string, deletes a range, and reads the string back,
 * verifying both the byte count and the round-tripped content.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "rope.h"

int main(void) {
    rope *r = rope_new();
    if (!r) { printf("FAIL: rope_new returned NULL\n"); return 1; }

    ROPE_RESULT ins = rope_insert(r, 0, (const uint8_t *)"Hi there!");
    if (ins != ROPE_OK) { printf("FAIL: rope_insert rc=%d\n", ins); return 1; }

    rope_del(r, 2, 6);
    if (rope_byte_count(r) != 3) { printf("FAIL: byte_count=%zu\n", rope_byte_count(r)); return 1; }

    uint8_t *str = rope_create_cstr(r);
    if (!str) { printf("FAIL: rope_create_cstr returned NULL\n"); return 1; }
    int ok = (strcmp((const char *)str, "Hi!") == 0);
    printf("%s: rope round-trip '%s'\n", ok ? "PASS" : "FAIL", (const char *)str);

    free(str);
    rope_free(r);
    return ok ? 0 : 1;
}
