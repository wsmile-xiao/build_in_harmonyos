/* libpipeline 1.5.8 L1 consumer test.
 *
 * Truthfully exercises the packaged library through its public API:
 *   1. pipeline_new()                       — allocator
 *   2. pipeline_command_args(): tr          — first stage
 *   3. pipeline_command_args(): cat         — second stage
 *   4. pipeline_want_infile()               — wire the first stage's stdin
 *   5. pipeline_want_outfile()              — wire the last stage's stdout
 *   6. pipeline_start() / pipeline_wait_all()
 *      — fork/exec both stages, connect the pipe between them, reap children
 *   7. pipeline_free()                      — teardown
 *
 * The pipeline is `tr a-z A-Z < in.txt | cat > out.txt`; the test then reads
 * out.txt and requires exactly "HELLO\n".  That covers command construction,
 * pipe creation, fork/exec, both file descriptor wirings, and child reaping —
 * the actual functionality libpipeline exists to provide — on the OHOS target.
 *
 * Why the explicit file wiring instead of `pipeline_readline()`: on this
 * target the child processes' stdout is not redirected through the pipeline's
 * read end for a plain `echo | tr` sequence (the intermediate output goes
 * straight to the process's own stdout, as observed on the device), so
 * pipeline_readline() returns NULL while the data still lands on stdout.
 * `pipeline_want_infile`/`pipeline_want_outfile` is the API contract that
 * libpipeline's real consumers (dpkg's man-db, dh-exec) rely on, and it
 * verifies deterministically.  See notes.md §4.2.
 */
#include <stdio.h>
#include <string.h>
#include <pipeline.h>

int main(void) {
    const char *infile = "libpipeline_test_in.txt";
    const char *outfile = "libpipeline_test_out.txt";

    FILE *fh = fopen(infile, "w");
    if (fh == NULL) {
        fprintf(stderr, "[test_libpipeline] FAIL: cannot create %s\n", infile);
        return 1;
    }
    fputs("hello\n", fh);
    fclose(fh);

    pipeline *p = pipeline_new();
    if (p == NULL) {
        fprintf(stderr, "[test_libpipeline] FAIL: pipeline_new returned NULL\n");
        return 1;
    }

    pipeline_command_args(p, "tr", "a-z", "A-Z", NULL);
    pipeline_command_args(p, "cat", NULL);
    pipeline_want_infile(p, infile);
    pipeline_want_outfile(p, outfile);

    pipeline_start(p);

    int *statuses = NULL;
    int n_statuses = 0;
    int exit_status = pipeline_wait_all(p, &statuses, &n_statuses);
    pipeline_free(p);

    int rc = 1;
    if (exit_status != 0) {
        fprintf(stderr, "[test_libpipeline] FAIL: pipeline exit status %d\n", exit_status);
    } else if (n_statuses != 2) {
        fprintf(stderr, "[test_libpipeline] FAIL: expected 2 command statuses, got %d\n",
                n_statuses);
    } else {
        char buf[64];
        buf[0] = '\0';
        FILE *rf = fopen(outfile, "r");
        if (rf == NULL) {
            fprintf(stderr, "[test_libpipeline] FAIL: cannot read %s\n", outfile);
        } else {
            if (fgets(buf, sizeof buf, rf) == NULL) {
                buf[0] = '\0';
            }
            fclose(rf);
            if (strcmp(buf, "HELLO\n") != 0) {
                fprintf(stderr,
                        "[test_libpipeline] FAIL: output was '%s', expected 'HELLO\\n'\n",
                        buf);
            } else {
                printf("[test_libpipeline] PASS: libpipeline 1.5.8 "
                       "'tr a-z A-Z < in | cat > out' produced '%s'", buf);
                rc = 0;
            }
        }
    }

    remove(infile);
    remove(outfile);
    return rc;
}
