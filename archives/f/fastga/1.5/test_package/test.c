#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/wait.h>

static int nonempty(const char *path)
{
    struct stat state;
    return stat(path, &state) == 0 && state.st_size > 0;
}

int main(int argc, char **argv)
{
    FILE *fasta;
    char command[4096];
    int i;
    int status;

    if (argc != 2) {
        fprintf(stderr, "expected path to packaged FAtoGDB\n");
        return 2;
    }

    fasta = fopen("input.fasta", "w");
    if (fasta == NULL)
        return 3;
    fputs(">masked-contig\n", fasta);
    for (i = 0; i < 8192; ++i)
        fputc((i % 97 < 8) ? "acgt"[i % 4] : "ACGT"[i % 4], fasta);
    fputc('\n', fasta);
    fclose(fasta);

    if (snprintf(command, sizeof(command), "TMPDIR=. \"%s\" input.fasta output",
                 argv[1]) >= (int)sizeof(command))
        return 4;
    status = system(command);
    if (status == -1 || !WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        fprintf(stderr, "packaged FAtoGDB failed with status %d\n", status);
        return 1;
    }
    if (!nonempty("output.1gdb") || !nonempty(".output.bps")) {
        fprintf(stderr, "FAtoGDB did not create non-empty GDB outputs\n");
        return 1;
    }
    return 0;
}
