#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lhasa.h>

/* Test that lhasa decoder API works correctly */
int main(void)
{
    const LHADecoderType *dtype;
    int ret = 0;

    /* Test 1: lha_decoder_for_name - known decoder type */
    dtype = lha_decoder_for_name("-lh1-");
    if (dtype == NULL) {
        printf("FAIL: lha_decoder_for_name(\"-lh1-\") returned NULL\n");
        ret = 1;
    } else {
        printf("PASS: lha_decoder_for_name(\"-lh1-\") found decoder\n");
    }

    /* Test 2: lha_decoder_for_name - another known decoder type */
    dtype = lha_decoder_for_name("-lh5-");
    if (dtype == NULL) {
        printf("FAIL: lha_decoder_for_name(\"-lh5-\") returned NULL\n");
        ret = 1;
    } else {
        printf("PASS: lha_decoder_for_name(\"-lh5-\") found decoder\n");
    }

    /* Test 3: lha_decoder_for_name - unknown decoder type returns NULL */
    dtype = lha_decoder_for_name("----");
    if (dtype != NULL) {
        printf("FAIL: lha_decoder_for_name(\"----\") should return NULL\n");
        ret = 1;
    } else {
        printf("PASS: lha_decoder_for_name(\"----\") returned NULL for unknown type\n");
    }

    /* Test 4: LHAFileHeader constants */
    printf("PASS: LHA_COMPRESS_TYPE_DIR = \"%s\"\n", LHA_COMPRESS_TYPE_DIR);
    printf("PASS: LHA_OS_TYPE_UNIX = '%c'\n", LHA_OS_TYPE_UNIX);

    return ret;
}