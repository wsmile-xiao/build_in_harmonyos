/* test_ddpt.c — drive the installed ddpt binary through real copy jobs and
 * assert actual behaviour (R34). The upstream testing/ scripts need SCSI/ram
 * block devices; regular-file copies need no privileges and are what a
 * consumer can exercise anywhere:
 *
 *   1. -V                                   -> exit 0, banner contains "0.97"
 *   2. if=<100000 LCG bytes> of=<out> bs=4096 -> exit 0, output byte-identical
 *   3. if=/dev/zero of=<out> bs=4096 count=2  -> exit 0, 8192 zero bytes
 *   4. if=<missing>                          -> non-zero exit, access error
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

#define IN_SIZE 100000

struct result {
    int exit_code;
    char output[4096];
};

static int failures = 0;

static struct result run_ddpt(const char *bin, const char *args) {
    struct result r;
    char cmd[2048];
    snprintf(cmd, sizeof cmd, "\"%s\" %s 2>&1", bin, args);
    r.exit_code = -1;
    r.output[0] = '\0';

    FILE *p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "FAIL: popen(%s)\n", cmd);
        failures++;
        return r;
    }
    size_t n = fread(r.output, 1, sizeof r.output - 1, p);
    r.output[n] = '\0';
    int status = pclose(p);
    if (WIFEXITED(status))
        r.exit_code = WEXITSTATUS(status);
    return r;
}

static void check(int cond, const char *what) {
    if (cond)
        printf("PASS: %s\n", what);
    else {
        fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    }
}

/* Deterministic 100000-byte input (32-bit LCG), so the comparison does not
 * depend on /dev/urandom being available. */
static int write_input(const char *path) {
    FILE *f = fopen(path, "wb");
    if (!f)
        return -1;
    unsigned int lcg = 12345u;
    for (int i = 0; i < IN_SIZE; i++) {
        lcg = lcg * 1103515245u + 12345u;
        unsigned char byte = (unsigned char)(lcg >> 16);
        if (fwrite(&byte, 1, 1, f) != 1) {
            fclose(f);
            return -1;
        }
    }
    fclose(f);
    return 0;
}

static unsigned char *read_all(const char *path, long *out_size) {
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    unsigned char *buf = malloc(size > 0 ? (size_t)size : 1);
    if (!buf || (size > 0 && fread(buf, 1, (size_t)size, f) != (size_t)size)) {
        free(buf);
        fclose(f);
        return NULL;
    }
    fclose(f);
    *out_size = size;
    return buf;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <ddpt-binary>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];
    struct result r;

    /* 1. version banner. */
    r = run_ddpt(bin, "-V");
    check(r.exit_code == 0, "ddpt -V exits 0");
    check(strstr(r.output, "0.97") != NULL, "ddpt -V reports version 0.97");

    /* 2. regular file -> regular file copy, byte-identical. */
    if (write_input("ddpt_in.bin") != 0) {
        fprintf(stderr, "FAIL: cannot create ddpt_in.bin\n");
        failures++;
        return 1;
    }
    r = run_ddpt(bin, "if=ddpt_in.bin of=ddpt_out.bin bs=4096");
    check(r.exit_code == 0, "ddpt file copy exits 0");

    long in_size = 0, out_size = 0;
    unsigned char *in_buf = read_all("ddpt_in.bin", &in_size);
    unsigned char *out_buf = read_all("ddpt_out.bin", &out_size);
    check(in_buf && out_buf && in_size == IN_SIZE && out_size == IN_SIZE,
          "ddpt copy preserves the input size (100000 bytes)");
    check(in_buf && out_buf && memcmp(in_buf, out_buf, IN_SIZE) == 0,
          "ddpt copy is byte-identical");
    free(in_buf);
    free(out_buf);

    /* 3. /dev/zero with a fixed count: exact size, all zero bytes. */
    r = run_ddpt(bin, "if=/dev/zero of=ddpt_zeros.bin bs=4096 count=2");
    check(r.exit_code == 0, "ddpt /dev/zero copy exits 0");
    long zeros_size = 0;
    unsigned char *zeros = read_all("ddpt_zeros.bin", &zeros_size);
    int all_zero = (zeros != NULL);
    if (all_zero) {
        for (long i = 0; i < zeros_size; i++) {
            if (zeros[i] != 0) {
                all_zero = 0;
                break;
            }
        }
    }
    check(zeros_size == 8192, "ddpt /dev/zero copy produces exactly 8192 bytes");
    check(all_zero, "ddpt /dev/zero copy contains only zero bytes");
    free(zeros);

    /* 4. missing input file: clean failure, not a silent success. */
    r = run_ddpt(bin, "if=ddpt_no_such_file.bin of=ddpt_x.bin bs=512");
    check(r.exit_code != 0, "ddpt with a missing input exits non-zero");
    check(strstr(r.output, "unable to access") != NULL,
          "ddpt with a missing input reports the access error");

    remove("ddpt_in.bin");
    remove("ddpt_out.bin");
    remove("ddpt_zeros.bin");
    remove("ddpt_x.bin");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("all ddpt behaviour checks passed\n");
    return 0;
}
