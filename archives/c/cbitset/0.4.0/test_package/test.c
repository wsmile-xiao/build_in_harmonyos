#include <cbitset/bitset.h>

int main(void) {
    bitset_t *bits = bitset_create();
    if (bits == NULL) {
        return 1;
    }

    bitset_set(bits, 2);
    bitset_set(bits, 65);
    if (bitset_count(bits) != 2 || !bitset_get(bits, 2) ||
        !bitset_get(bits, 65) || bitset_get(bits, 3) ||
        bitset_minimum(bits) != 2 || bitset_maximum(bits) != 65) {
        bitset_free(bits);
        return 2;
    }

    size_t next = 0;
    if (!bitset_next_set_bit(bits, &next) || next != 2) {
        bitset_free(bits);
        return 3;
    }
    next++;
    if (!bitset_next_set_bit(bits, &next) || next != 65) {
        bitset_free(bits);
        return 4;
    }

    bitset_clear(bits);
    if (!bitset_empty(bits)) {
        bitset_free(bits);
        return 5;
    }
    bitset_free(bits);
    return 0;
}
