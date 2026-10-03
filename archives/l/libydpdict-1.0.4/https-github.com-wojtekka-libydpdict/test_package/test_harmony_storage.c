/* Exercise a dictionary installed under HarmonyOS PC's actual user storage. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <ydpdict/ydpdict.h>
#include "dictionary_fixture.h"

int main(void)
{
    struct utsname platform;
    char directory[256], dat[320], idx[320], staged_dat[320], staged_idx[320];
    ydpdict_t *dict = NULL;
    char *definition = NULL;
    const char *word;
    int result = 1;
    if (uname(&platform) || strcmp(platform.sysname, "HarmonyOS") != 0) {
        fprintf(stderr, "This storage workflow requires a real HarmonyOS kernel\n");
        return 1;
    }
    snprintf(directory, sizeof(directory),
             "/storage/Users/currentUser/ydpdict-词典-%ld", (long)getpid());
    snprintf(dat, sizeof(dat), "%s/词典.dat", directory);
    snprintf(idx, sizeof(idx), "%s/词典.idx", directory);
    snprintf(staged_dat, sizeof(staged_dat), "%s/staged.dat", directory);
    snprintf(staged_idx, sizeof(staged_idx), "%s/staged.idx", directory);
    if (mkdir(directory, 0770) || chmod(directory, 02770)) {
        perror("HarmonyOS user storage directory");
        return 1;
    }
    printf("HarmonyOS storage: %s %s, %s\n", platform.sysname, platform.machine, directory);
    if (make_dict(staged_dat, staged_idx) || rename(staged_dat, dat) || rename(staged_idx, idx)) {
        perror("write and rename dictionary on user storage");
        goto cleanup;
    }
    dict = ydpdict_open(dat, idx, YDPDICT_ENCODING_UTF8);
    if (!dict) { perror("open installed dictionary"); goto cleanup; }
    word = ydpdict_get_word(dict, 2);
    definition = ydpdict_read_rtf(dict, 2);
    if (ydpdict_get_count(dict) != 3 || ydpdict_find_word(dict, "s\xc5\x82owo") != 2 ||
        !word || strcmp(word, "s\xc5\x82owo") || !definition || strcmp(definition, fixture_defs[2])) {
        fprintf(stderr, "installed dictionary lookup failed\n");
        goto cleanup;
    }
    free(definition);
    definition = NULL;
    if (ydpdict_close(dict)) { dict = NULL; goto cleanup; }
    dict = NULL;
    /* Reopen the persisted files after closing all library handles. */
    dict = ydpdict_open(dat, idx, YDPDICT_ENCODING_UTF8);
    if (!dict || ydpdict_find_word(dict, "SHIELD") != 1) goto cleanup;
    if (ydpdict_close(dict)) { dict = NULL; goto cleanup; }
    dict = NULL;
    result = 0;
cleanup:
    free(definition);
    if (dict) ydpdict_close(dict);
    /* Either stage may already have been renamed. */
    if (access(staged_dat, F_OK) == 0 && remove(staged_dat)) result = 1;
    if (access(staged_idx, F_OK) == 0 && remove(staged_idx)) result = 1;
    if (access(dat, F_OK) == 0 && remove(dat)) result = 1;
    if (access(idx, F_OK) == 0 && remove(idx)) result = 1;
    if (rmdir(directory)) result = 1;
    printf("HarmonyOS storage workflow: %s\n", result ? "FAILED" : "OK");
    return result;
}
