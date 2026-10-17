#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int write_fasta(const char *path, const char *name, const char *sequence)
{
    FILE *fp = fopen(path, "w");

    if (fp == NULL) {
        return 1;
    }

    if (fprintf(fp, ">%s\n%s\n", name, sequence) < 0) {
        fclose(fp);
        return 1;
    }

    if (fclose(fp) != 0) {
        return 1;
    }

    return 0;
}

int main(int argc, char **argv)
{
    const char *sequence =
        "ACGTACGTACGTACGTACGTACGTACGTACGT"
        "ACGTACGTACGTACGTACGTACGTACGTACGT"
        "ACGTACGTACGTACGTACGTACGTACGTACGT";

    char target[4096];
    char query[4096];
    char result[4096];
    char command[16384];
    struct stat st;
    FILE *fp;
    char line[4096];
    int found_target = 0;
    int found_query = 0;
    int rc;

    if (argc != 3) {
        fprintf(stderr, "usage: %s <lastz> <workdir>\n", argv[0]);
        return 10;
    }

    if (snprintf(
            target,
            sizeof(target),
            "%s/target.fa",
            argv[2]
        ) >= (int) sizeof(target)) {
        return 11;
    }

    if (snprintf(
            query,
            sizeof(query),
            "%s/query.fa",
            argv[2]
        ) >= (int) sizeof(query)) {
        return 12;
    }
    if (snprintf(
            result,
            sizeof(result),
            "%s/result.lav",
            argv[2]
        ) >= (int) sizeof(result)) {
        return 13;
    }

    if (write_fasta(target, "target", sequence) != 0) {
        fprintf(stderr, "failed to create target FASTA\n");
        return 14;
    }

    if (write_fasta(query, "query", sequence) != 0) {
        fprintf(stderr, "failed to create query FASTA\n");
        return 15;
    }

    if (snprintf(
            command,
            sizeof(command),
            "\"%s\" \"%s\" \"%s\" > \"%s\"",
            argv[1],
            target,
            query,
            result
        ) >= (int) sizeof(command)) {
        fprintf(stderr, "command too long\n");
        return 16;
    }

    rc = system(command);

    if (rc != 0) {
        fprintf(stderr, "lastz execution failed: %d\n", rc);
        return 1;
    }

    if (stat(result, &st) != 0) {
        fprintf(stderr, "lastz did not create alignment output\n");
        return 2;
    }

    if (st.st_size <= 0) {
        fprintf(stderr, "lastz alignment output is empty\n");
        return 3;
    }

    fp = fopen(result, "r");

    if (fp == NULL) {
        fprintf(stderr, "unable to open alignment output\n");
        return 17;
    }

    while (fgets(line, sizeof(line), fp) != NULL) {
        if (strstr(line, "target") != NULL) {
            found_target = 1;
        }

        if (strstr(line, "query") != NULL) {
            found_query = 1;
        }
    }

    fclose(fp);

    if (!found_target) {
        fprintf(stderr, "target sequence missing from output\n");
        return 4;
    }

    if (!found_query) {
        fprintf(stderr, "query sequence missing from output\n");
        return 5;
    }

    puts("lastz consumer alignment test passed");

    return 0;
}
