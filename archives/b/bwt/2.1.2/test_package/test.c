#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* bwt library API */
#include "bwxform.h"

static char TEST_FILE[512];
static char ENC_FILE[512];
static char DEC_FILE[512];

static void build_paths(void) {
    const char *tmp = getenv("TMPDIR");
    if (!tmp) {
        const char *home = getenv("HOME");
        if (home) {
            snprintf(TEST_FILE, sizeof(TEST_FILE), "%s/bwt_test_input.txt", home);
            snprintf(ENC_FILE, sizeof(ENC_FILE), "%s/bwt_test_encoded.bin", home);
            snprintf(DEC_FILE, sizeof(DEC_FILE), "%s/bwt_test_decoded.txt", home);
            return;
        }
        strcpy(TEST_FILE, "bwt_test_input.txt");
        strcpy(ENC_FILE, "bwt_test_encoded.bin");
        strcpy(DEC_FILE, "bwt_test_decoded.txt");
        return;
    }
    snprintf(TEST_FILE, sizeof(TEST_FILE), "%s/bwt_test_input.txt", tmp);
    snprintf(ENC_FILE, sizeof(ENC_FILE), "%s/bwt_test_encoded.bin", tmp);
    snprintf(DEC_FILE, sizeof(DEC_FILE), "%s/bwt_test_decoded.txt", tmp);
}

static int run_roundtrip(xform_t method, const char *label) {
    FILE *fp;
    FILE *fpEnc;
    char input[] = "The quick brown fox jumps over the lazy dog. Testing BWT.";
    char buf[256];
    int ret = 0;

    /* Write test input */
    fp = fopen(TEST_FILE, "w");
    if (!fp) {
        perror("fopen input");
        return 1;
    }
    fputs(input, fp);
    fclose(fp);

    /* Encode */
    fp = fopen(TEST_FILE, "r");
    if (!fp) {
        perror("fopen input for read");
        return 1;
    }
    fpEnc = fopen(ENC_FILE, "w");
    if (!fpEnc) {
        perror("fopen enc");
        fclose(fp);
        return 1;
    }
    if (BWXform(fp, fpEnc, method) != 0) {
        printf("FAIL: BWXform encode returned error\n");
        ret = 1;
    }
    fclose(fp);
    fclose(fpEnc);

    /* Decode */
    fpEnc = fopen(ENC_FILE, "r");
    if (!fpEnc) {
        perror("fopen enc for read");
        return 1;
    }
    fp = fopen(DEC_FILE, "w");
    if (!fp) {
        perror("fopen dec");
        fclose(fpEnc);
        return 1;
    }
    if (BWReverseXform(fpEnc, fp, method) != 0) {
        printf("FAIL: BWReverseXform decode returned error\n");
        ret = 1;
    }
    fclose(fpEnc);
    fclose(fp);

    /* Verify roundtrip */
    fp = fopen(DEC_FILE, "r");
    if (!fp) {
        perror("fopen dec for read");
        return 1;
    }
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        printf("FAIL: roundtrip mismatch (%s)\n  expected: %s\n  got:      <empty>\n",
               label, input);
        ret = 1;
    } else if (strcmp(buf, input) != 0) {
        printf("FAIL: roundtrip mismatch (%s)\n  expected: %s\n  got:      %s\n",
               label, input, buf);
        ret = 1;
    } else {
        printf("PASS: BWT roundtrip encode/decode %s OK\n", label);
    }
    fclose(fp);

    /* Cleanup */
    remove(TEST_FILE);
    remove(ENC_FILE);
    remove(DEC_FILE);
    return ret;
}

int main(void) {
    int ret = 0;

    build_paths();

    ret |= run_roundtrip(XFORM_WITHOUT_MTF, "without MTF");
    ret |= run_roundtrip(XFORM_WITH_MTF, "with MTF");

    if (ret == 0)
        printf("All bwt tests passed!\n");
    return ret;
}