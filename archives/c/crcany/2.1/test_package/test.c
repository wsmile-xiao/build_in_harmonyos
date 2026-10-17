#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "crc.h"
#include "model.h"

/* Consumer test for the packaged crcany static library.
 * Exercises the real public API (model.h + crc.h) against the well-known
 * CRC-32/ISO-HDLC vector: CRC("123456789") == 0xCBF43926.
 * Five checks, each prints a PASS line with the computed value so the log
 * shows real non-zero evidence (not empty-to-empty comparisons).
 */
int main(void)
{
    char desc[] = "width=32 poly=0x04C11DB7 init=0xFFFFFFFF refin=true "
                  "refout=true xorout=0xFFFFFFFF check=0xCBF43926 "
                  "residue=0xDEBB20E3 name=\"CRC-32/ISO-HDLC\"";
    static const unsigned char msg[] = "123456789";
    const size_t len = 9;
    const word_t expected = (word_t)0xCBF43926UL;
    model_t model;
    word_t crc;
    unsigned little = 1;

    memset(&model, 0, sizeof(model));
    if (read_model(&model, desc, 0) != 0) {
        fprintf(stderr, "FAIL read_model: rejected CRC-32/ISO-HDLC description\n");
        return 1;
    }
    if (model.width != 32 || model.check != expected ||
        model.name == NULL || strcmp(model.name, "CRC-32/ISO-HDLC") != 0) {
        fprintf(stderr, "FAIL model fields: width=%u check=0x%lX name=%s\n",
                model.width, (unsigned long)model.check,
                model.name ? model.name : "<null>");
        return 1;
    }
    printf("PASS model-parse: width=32 check=0xCBF43926 name=CRC-32/ISO-HDLC\n");

    process_model(&model);
    crc_table_combine(&model);
    crc_table_bytewise(&model);
    little = *((unsigned char *)&little);
    crc_table_wordwise(&model, little, WORDBITS);

    crc = crc_bitwise(&model, 0, NULL, 0);
    crc = crc_bitwise(&model, crc, msg, len);
    if (crc != expected || crc == 0) {
        fprintf(stderr, "FAIL bitwise: got 0x%lX, want 0xCBF43926\n", (unsigned long)crc);
        return 1;
    }
    printf("PASS bitwise: 0x%lX\n", (unsigned long)crc);

    crc = crc_bytewise(&model, 0, NULL, 0);
    crc = crc_bytewise(&model, crc, msg, len);
    if (crc != expected || crc == 0) {
        fprintf(stderr, "FAIL bytewise: got 0x%lX, want 0xCBF43926\n", (unsigned long)crc);
        return 1;
    }
    printf("PASS bytewise: 0x%lX\n", (unsigned long)crc);

    crc = crc_wordwise(&model, 0, NULL, 0);
    crc = crc_wordwise(&model, crc, msg, len);
    if (crc != expected || crc == 0) {
        fprintf(stderr, "FAIL wordwise: got 0x%lX, want 0xCBF43926\n", (unsigned long)crc);
        return 1;
    }
    printf("PASS wordwise: 0x%lX\n", (unsigned long)crc);

    {
        word_t init = crc_bytewise(&model, 0, NULL, 0);
        word_t full = crc_bytewise(&model, init, msg, len);
        word_t first = crc_bytewise(&model, init, msg, 5);
        word_t second = crc_bytewise(&model, init, msg + 5, len - 5);
        word_t joined = crc_combine(&model, first, second, (uintmax_t)(len - 5));
        if (joined != full || full != expected) {
            fprintf(stderr, "FAIL combine: joined=0x%lX full=0x%lX want 0xCBF43926\n",
                    (unsigned long)joined, (unsigned long)full);
            return 1;
        }
        printf("PASS combine: 0x%lX\n", (unsigned long)joined);
    }

    printf("All crcany consumer tests passed.\n");
    return 0;
}
