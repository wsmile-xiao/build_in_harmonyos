/* Consumer-side checker: reads `news` output on stdin and verifies it.
 * usage: check_news <expected-line-count> <name>...
 *   Every output line must be "NEWS: <name>" (news -nl format), the number of
 *   lines must equal <expected-line-count>, and each <name> must appear. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    char line[512];
    int lines = 0, found = 0, i;
    int seen[64] = {0};

    if (argc < 2 || argc > 60) {
        fprintf(stderr, "usage: %s count name...\n", argv[0]);
        return 2;
    }
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\n")] = 0;
        if (strncmp(line, "NEWS: ", 6) != 0) {
            fprintf(stderr, "unexpected line: %s\n", line);
            return 1;
        }
        lines++;
        for (i = 2; i < argc; i++)
            if (!seen[i] && strstr(line + 6, argv[i])) {
                seen[i] = 1;
                found++;
            }
    }
    if (lines != atoi(argv[1])) {
        fprintf(stderr, "line count %d != expected %s\n", lines, argv[1]);
        return 1;
    }
    if (found != argc - 2) {
        fprintf(stderr, "found %d of %d expected names\n", found, argc - 2);
        return 1;
    }
    printf("check_news: %d lines, %d names OK\n", lines, found);
    return 0;
}
