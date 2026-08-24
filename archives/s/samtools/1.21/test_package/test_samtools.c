/* samtools OHOS consumer test: ten independent runtime assertions. */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int run_command(const char *command, char *output, size_t output_size) {
    FILE *pipe = popen(command, "r");
    size_t used = 0;
    int status;

    if (!pipe) {
        return -1;
    }
    if (output_size > 0) {
        output[0] = '\0';
    }
    while (output_size > used + 1 && fgets(output + used, (int)(output_size - used), pipe)) {
        used = strlen(output);
    }
    status = pclose(pipe);
    if (status == -1 || !WIFEXITED(status)) {
        return -1;
    }
    return WEXITSTATUS(status);
}

static int contains(const char *output, const char *needle) {
    return strstr(output, needle) != NULL;
}

static int make_fixtures(const char *dir, char *sam, size_t sam_size,
                         char *fasta, size_t fasta_size) {
    FILE *file;
    int written;

    written = snprintf(sam, sam_size, "%s/input.sam", dir);
    if (written < 0 || (size_t)written >= sam_size) {
        return 0;
    }
    written = snprintf(fasta, fasta_size, "%s/reference.fa", dir);
    if (written < 0 || (size_t)written >= fasta_size) {
        return 0;
    }
    file = fopen(sam, "w");
    if (!file) {
        return 0;
    }
    fputs("@HD\tVN:1.6\tSO:coordinate\n"
          "@SQ\tSN:chr1\tLN:20\n"
          "r001\t0\tchr1\t1\t60\t5M\t*\t0\t0\tACGTA\tIIIII\n"
          "r002\t16\tchr1\t5\t50\t5M\t*\t0\t0\tTGCAT\tIIIII\n", file);
    fclose(file);

    file = fopen(fasta, "w");
    if (!file) {
        return 0;
    }
    fputs(">chr1\nACGTACGTACGTACGTACGT\n", file);
    fclose(file);
    return 1;
}

int main(int argc, char **argv) {
    const char *samtools = argc > 1 ? argv[1] : "samtools";
    const char *tmp = getenv("TMPDIR");
    char dir[512], sam[640], fasta[640], bam[640], sorted[640], index[640];
    char command[1600], output[8192];
    int passed = 0;
    int total = 10;
    int status;

    if (!tmp || !*tmp) {
        tmp = ".";
    }
    snprintf(dir, sizeof(dir), "%s/samtools-ohos-test-XXXXXX", tmp);
    if (!mkdtemp(dir) || !make_fixtures(dir, sam, sizeof(sam), fasta, sizeof(fasta))) {
        fprintf(stderr, "FAIL: cannot create test fixtures: %s\n", strerror(errno));
        return 1;
    }
    snprintf(bam, sizeof(bam), "%s/input.bam", dir);
    snprintf(sorted, sizeof(sorted), "%s/sorted.bam", dir);
    snprintf(index, sizeof(index), "%s/sorted.bam.bai", dir);

    snprintf(command, sizeof(command), "\"%s\" --version 2>&1", samtools);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && contains(output, "samtools 1.21")) passed++;

    snprintf(command, sizeof(command), "\"%s\" --help 2>&1", samtools);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && contains(output, "Usage:")) passed++;

    snprintf(command, sizeof(command), "\"%s\" view -h \"%s\" 2>&1", samtools, sam);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && contains(output, "@SQ\tSN:chr1") && contains(output, "r001")) passed++;

    snprintf(command, sizeof(command), "\"%s\" view -b -o \"%s\" \"%s\" 2>&1", samtools, bam, sam);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && access(bam, R_OK) == 0) passed++;

    snprintf(command, sizeof(command), "\"%s\" view -c \"%s\" 2>&1", samtools, bam);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && contains(output, "2")) passed++;

    snprintf(command, sizeof(command), "\"%s\" sort -o \"%s\" \"%s\" 2>&1", samtools, sorted, bam);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && access(sorted, R_OK) == 0) passed++;

    snprintf(command, sizeof(command), "\"%s\" index \"%s\" 2>&1", samtools, sorted);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && access(index, R_OK) == 0) passed++;

    snprintf(command, sizeof(command), "\"%s\" flagstat \"%s\" 2>&1", samtools, sorted);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && contains(output, "in total")) passed++;

    snprintf(command, sizeof(command), "\"%s\" quickcheck \"%s\" 2>&1", samtools, sorted);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && output[0] == '\0') passed++;

    snprintf(command, sizeof(command), "\"%s\" faidx \"%s\" chr1:1-5 2>&1", samtools, fasta);
    status = run_command(command, output, sizeof(output));
    if (status == 0 && contains(output, "ACGTA")) passed++;

    printf("samtools OHOS consumer assertions: %d/%d passed\n", passed, total);
    return passed == total ? 0 : 1;
}
