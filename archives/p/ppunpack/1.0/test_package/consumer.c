/*
 * ppunpack consumer (HarmonyOS PC case 7).
 *
 * An OHOS-native program, built with the OHOS NDK toolchain from the profile,
 * that uses the packaged ppunpack CLI the way an application would: it runs
 * the tool as a child process (fork + execv + waitpid), then checks the
 * restored data itself.  test_package delivers this very source file
 * PP20-packed and has ppunpack restore it before it is compiled.
 *
 * usage: consumer <ppunpack> <packed.pp> <expected> <workdir> [runner]
 *   runner: optional emulator (qemu-aarch64) used to start ppunpack when the
 *           test runs on a non-AArch64 host; empty on an AArch64 device.
 *
 * Checks:
 *   a) ppunpack <packed.pp> <workdir>/consumer.out exits 0 and the output is
 *      byte-identical to <expected>;
 *   b) ppunpack on a non-PP20 file (<expected> itself) exits 10 and writes
 *      no output file.
 * Exit status 0 only if both hold.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static const char *runner;

static int run_tool(const char *tool, const char *in, const char *out)
{
    char *argv[6];
    int n = 0;
    pid_t pid;
    int status;

    if (runner && runner[0])
        argv[n++] = (char *)runner;
    argv[n++] = (char *)tool;
    argv[n++] = (char *)in;
    argv[n++] = (char *)out;
    argv[n] = NULL;

    pid = fork();
    if (pid < 0) {
        perror("consumer: fork");
        return -1;
    }
    if (pid == 0) {
        execv(argv[0], argv);
        perror("consumer: execv");
        _exit(127);
    }
    if (waitpid(pid, &status, 0) != pid) {
        perror("consumer: waitpid");
        return -1;
    }
    if (!WIFEXITED(status)) {
        fprintf(stderr, "consumer: ppunpack did not exit normally (status 0x%x)\n", status);
        return -1;
    }
    return WEXITSTATUS(status);
}

static unsigned char *slurp(const char *path, long *len)
{
    FILE *f = fopen(path, "rb");
    unsigned char *buf;

    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END) != 0 || (*len = ftell(f)) < 0) {
        fclose(f);
        return NULL;
    }
    rewind(f);
    buf = malloc(*len ? (size_t)*len : 1);
    if (buf && fread(buf, 1, (size_t)*len, f) != (size_t)*len) {
        free(buf);
        buf = NULL;
    }
    fclose(f);
    return buf;
}

int main(int argc, char **argv)
{
    char out[4096], refused[4096];
    unsigned char *got, *exp;
    long got_len, exp_len;
    int rc;

    if (argc < 5 || argc > 6) {
        fprintf(stderr, "usage: %s <ppunpack> <packed.pp> <expected> <workdir> [runner]\n", argv[0]);
        return 2;
    }
    runner = argc == 6 ? argv[5] : NULL;
    snprintf(out, sizeof out, "%s/consumer.out", argv[4]);
    snprintf(refused, sizeof refused, "%s/consumer.refused", argv[4]);
    unlink(out);
    unlink(refused);

    /* a) restore through the CLI and verify the bytes */
    rc = run_tool(argv[1], argv[2], out);
    if (rc != 0) {
        fprintf(stderr, "consumer: ppunpack exit %d on %s\n", rc, argv[2]);
        return 1;
    }
    got = slurp(out, &got_len);
    exp = slurp(argv[3], &exp_len);
    if (!got || !exp) {
        fprintf(stderr, "consumer: cannot read %s or %s\n", out, argv[3]);
        return 1;
    }
    if (got_len != exp_len || memcmp(got, exp, (size_t)exp_len) != 0) {
        fprintf(stderr, "consumer: restored %ld bytes, expected %ld, content differs\n",
                got_len, exp_len);
        return 1;
    }
    printf("consumer: ppunpack restored %ld bytes, memcmp identical\n", got_len);

    /* b) a plain file must be refused with exit 10 and no output */
    rc = run_tool(argv[1], argv[3], refused);
    if (rc != 10 || access(refused, F_OK) == 0) {
        fprintf(stderr, "consumer: non-PP20 input gave exit %d (want 10), output %s\n",
                rc, access(refused, F_OK) == 0 ? "written" : "absent");
        return 1;
    }
    printf("consumer: non-PP20 input refused with exit 10\n");
    free(got);
    free(exp);
    printf("consumer ok\n");
    return 0;
}
