/* OHOS aarch64 consumer of the shfm package.
 *
 * This file is copied into a directory that the test picks with the packaged shfm
 * (cd-on-exit output), compiled from there and run *inside* that directory, i.e. the
 * way `cd "$(shfm)" && ./consumer` would use it.  The program checks that the working
 * directory really is the folder shfm printed (argv[1]) and holds the files that were
 * listed on shfm's screen.
 */
#include <dirent.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#if !defined(__aarch64__)
#error "the shfm consumer must be built for aarch64 (OHOS PC)"
#endif

int main(int argc, char **argv) {
    char cwd[PATH_MAX], want[PATH_MAX];
    int has_source = 0, has_notes = 0, others = 0;
    struct dirent *entry;
    DIR *dir;

    if (argc != 2 || realpath(argv[1], want) == NULL || getcwd(cwd, sizeof cwd) == NULL) {
        fprintf(stderr, "usage: consumer <dir printed by shfm>\n");
        return 2;
    }
    if (strcmp(cwd, want) != 0) {
        fprintf(stderr, "cwd %s is not the shfm-selected dir %s\n", cwd, want);
        return 3;
    }
    dir = opendir(".");
    if (dir == NULL) {
        perror("opendir");
        return 4;
    }
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0)
            continue;
        if (strcmp(entry->d_name, "consumer.c") == 0)
            has_source = 1;
        else if (strcmp(entry->d_name, "notes.txt") == 0)
            has_notes = 1;
        else
            others++;
    }
    closedir(dir);
    if (!has_source || !has_notes || others != 0) {
        fprintf(stderr, "unexpected directory contents (consumer.c=%d notes.txt=%d other=%d)\n",
                has_source, has_notes, others);
        return 5;
    }
    printf("shfm cd-on-exit dir %s: consumer.c + notes.txt, built and run for OHOS aarch64\n", cwd);
    return 0;
}
