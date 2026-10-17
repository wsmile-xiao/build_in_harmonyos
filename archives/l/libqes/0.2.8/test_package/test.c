#include <stdio.h>
#include <string.h>
#include <qes.h>

int main(void) {
    int failures = 0;

    /* 1. create + basic validity */
    struct qes_seq *seq = qes_seq_create();
    if (seq == NULL) {
        fprintf(stderr, "FAIL: qes_seq_create returned NULL\n");
        return 1;
    }
    if (!qes_seq_ok(seq)) {
        fprintf(stderr, "FAIL: fresh seq not ok\n");
        failures++;
    } else {
        printf("PASS: qes_seq_create ok\n");
    }

    /* 2. fill name/seq and re-validate.
       Upstream API (src/qes_seq.c + test/test_seq.c): qes_seq_fill_*
       returns 0 on success, 1 on failure, and len==0 is a failure
       (only qes_seq_fill_header treats 0 as strlen). So pass explicit
       lengths and test for != 0. The previous revision used
       !fill(..., 0) which mistook the failure return (1) for success,
       leaving seq empty and causing the later content/truncate FAILs. */
    if (qes_seq_fill_name(seq, "test_read", 9) != 0) {
        fprintf(stderr, "FAIL: qes_seq_fill_name\n");
        failures++;
    } else {
        printf("PASS: fill_name len=%d\n", (int)seq->name.len);
    }
    if (qes_seq_fill_seq(seq, "ACGTACGT", 8) != 0) {
        fprintf(stderr, "FAIL: qes_seq_fill_seq\n");
        failures++;
    } else {
        printf("PASS: fill_seq len=%d\n", (int)seq->seq.len);
    }
    if (!qes_seq_ok(seq)) {
        fprintf(stderr, "FAIL: filled seq not ok\n");
        failures++;
    } else {
        printf("PASS: filled seq ok\n");
    }
    if (seq->seq.len != 8 || strncmp(seq->seq.str, "ACGTACGT", 8) != 0) {
        fprintf(stderr, "FAIL: seq content mismatch\n");
        failures++;
    } else {
        printf("PASS: seq content match\n");
    }

    /* 3. string helper path (exercises qes_str via seq comment) */
    if (qes_seq_fill_comment(seq, "demo", 4) != 0) {
        fprintf(stderr, "FAIL: qes_seq_fill_comment\n");
        failures++;
    } else {
        printf("PASS: fill_comment len=%d\n", (int)seq->comment.len);
    }

    /* 4. truncate exercises qes_seq_truncate + qes_str_truncate
       (0 on success, non-zero on failure). */
    if (qes_seq_truncate(seq, 4) != 0) {
        fprintf(stderr, "FAIL: qes_seq_truncate\n");
        failures++;
    } else {
        printf("PASS: truncate to 4\n");
    }
    if (seq->seq.len != 4) {
        fprintf(stderr, "FAIL: truncate len=%d\n", (int)seq->seq.len);
        failures++;
    } else {
        printf("PASS: truncated len ok\n");
    }

    qes_seq_destroy(seq);

    if (failures == 0) {
        printf("test libqes 0.2.8: OK (8 assertions passed)\n");
        return 0;
    }
    fprintf(stderr, "test libqes 0.2.8: %d FAILURES\n", failures);
    return 1;
}
