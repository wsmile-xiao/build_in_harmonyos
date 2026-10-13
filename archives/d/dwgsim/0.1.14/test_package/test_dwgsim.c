/*
 * Consumer test for dwgsim/0.1.14 (Conan L1).
 *
 * The package ships command line tools, so the test drives them end to end
 * instead of linking a library (R34):
 *
 *   1. write a deterministic two-sequence reference FASTA,
 *   2. run <bin>/dwgsim -N 100 on it and assert all five simulator outputs
 *      are created and non-empty,
 *   3. run <bin>/dwgsim_eval -h and assert its usage banner is printed.
 *
 * Everything is launched with fork/execv + waitpid, so the test does not
 * depend on a shell.
 */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int run_capture(char *const argv[], const char *outfile)
{
    pid_t pid;
    int status = 0;

    pid = fork();
    if (pid < 0) {
        perror("fork");
        return -1;
    }
    if (pid == 0) {
        if (outfile != NULL) {
            int fd = open(outfile, O_WRONLY | O_CREAT | O_TRUNC, 0644);
            if (fd >= 0) {
                dup2(fd, 1);
                dup2(fd, 2);
                close(fd);
            }
        }
        execv(argv[0], argv);
        _exit(127);
    }
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return -1;
    }
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

static int run(char *const argv[])
{
    return run_capture(argv, NULL);
}

static long file_size(const char *path)
{
    struct stat st;
    if (stat(path, &st) != 0) {
        return -1L;
    }
    return (long)st.st_size;
}

/* Two deterministic 1500 bp sequences; long enough for dwgsim to place
 * -N 100 pairs with the default outer distance of 500. */
static int write_reference(const char *path)
{
    static const char *names[2] = {"chr1", "chr2"};
    unsigned long seed = 12345UL;
    FILE *fh = fopen(path, "w");
    int n, i;

    if (fh == NULL) {
        perror(path);
        return -1;
    }
    for (n = 0; n < 2; n++) {
        fprintf(fh, ">%s\n", names[n]);
        for (i = 0; i < 1500; i++) {
            seed = seed * 6364136223846793005UL + 1442695040888963407UL;
            fputc("ACGT"[(seed >> 33) & 3], fh);
            if ((i + 1) % 60 == 0) {
                fputc('\n', fh);
            }
        }
        fputc('\n', fh);
    }
    fclose(fh);
    return 0;
}

int main(int argc, char **argv)
{
    static const char *outputs[] = {
        "out.bfast.fastq.gz",
        "out.bwa.read1.fastq.gz",
        "out.bwa.read2.fastq.gz",
        "out.mutations.txt",
        "out.mutations.vcf",
    };
    char dwgsim[4096];
    char dwgsim_eval[4096];
    char help[4096];
    char *dwgsim_argv[6];
    char *eval_argv[3];
    char buffer[8192];
    FILE *fh;
    size_t got;
    size_t i;
    int rc;

    if (argc < 3) {
        fprintf(stderr, "usage: test_dwgsim <dwgsim> <dwgsim_eval>\n");
        return 1;
    }
    snprintf(dwgsim, sizeof(dwgsim), "%s", argv[1]);
    snprintf(dwgsim_eval, sizeof(dwgsim_eval), "%s", argv[2]);

    if (write_reference("ref.fa") != 0) {
        return 1;
    }

    dwgsim_argv[0] = dwgsim;
    dwgsim_argv[1] = "-N";
    dwgsim_argv[2] = "100";
    dwgsim_argv[3] = "ref.fa";
    dwgsim_argv[4] = "out";
    dwgsim_argv[5] = NULL;
    rc = run(dwgsim_argv);
    if (rc != 0) {
        fprintf(stderr, "FAIL: dwgsim exited with %d\n", rc);
        return 1;
    }
    printf("PASS: dwgsim -N 100 ref.fa out (exit 0)\n");

    for (i = 0; i < sizeof(outputs) / sizeof(outputs[0]); i++) {
        long size = file_size(outputs[i]);
        if (size <= 0) {
            fprintf(stderr, "FAIL: missing or empty output %s (%ld bytes)\n",
                    outputs[i], size);
            return 1;
        }
        printf("PASS: %s (%ld bytes)\n", outputs[i], size);
    }

    snprintf(help, sizeof(help), "%s.eval_help.txt", "out");
    eval_argv[0] = dwgsim_eval;
    eval_argv[1] = "-h";
    eval_argv[2] = NULL;
    rc = run_capture(eval_argv, help);
    fh = fopen(help, "r");
    if (fh == NULL) {
        fprintf(stderr, "FAIL: dwgsim_eval produced no captured output\n");
        return 1;
    }
    got = fread(buffer, 1, sizeof(buffer) - 1, fh);
    fclose(fh);
    buffer[got] = '\0';
    if (rc != 1 || strstr(buffer, "Usage: dwgsim_eval") == NULL) {
        fprintf(stderr, "FAIL: dwgsim_eval -h (exit %d) did not print its usage\n", rc);
        return 1;
    }
    printf("PASS: dwgsim_eval -h prints the usage banner (exit %d)\n", rc);

    printf("ALL TESTS PASSED\n");
    return 0;
}
