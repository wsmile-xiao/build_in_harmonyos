#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ydpdict/ydpdict.h>
#include "dictionary_fixture.h"

static int failures;
static void check(int condition, const char *message)
{
    printf("[%s] %s\n", condition ? "ok" : "FAIL", message);
    if (!condition) ++failures;
}

int main(void)
{
    char dat[128], idx[128];
    const char *word;
    char *rtf;
    ydpdict_t *dict;
    snprintf(dat, sizeof(dat), "ydpdict-%ld.dat", (long)getpid());
    snprintf(idx, sizeof(idx), "ydpdict-%ld.idx", (long)getpid());
    check(make_dict(dat, idx) == 0, "write a real dictionary pair");
    dict = ydpdict_open(dat, idx, YDPDICT_ENCODING_UTF8);
    check(dict != NULL, "open dictionary in UTF8 mode");
    if (dict) {
        check(ydpdict_get_count(dict) == 3, "three entries");
        check(ydpdict_find_word(dict, "COMPU") == 0, "case insensitive prefix search");
        word = ydpdict_get_word(dict, 0);
        check(word && strcmp(word, "computer") == 0, "read headword");
        check(ydpdict_find_word(dict, "s\xc5\x82owo") == 2, "find converted UTF8 headword");
        word = ydpdict_get_word(dict, 2);
        check(word && strcmp(word, "s\xc5\x82owo") == 0, "Windows1250 headword converted to UTF8");
        rtf = ydpdict_read_rtf(dict, 1);
        check(rtf && strcmp(rtf, fixture_defs[1]) == 0, "read raw definition at nonzero offset");
        free(rtf);
        errno = 0;
        rtf = ydpdict_read_rtf(dict, 3);
        check(!rtf && errno == EINVAL, "out of range definition sets EINVAL");
        free(rtf);
        check(ydpdict_find_word(dict, "absent") == -1, "missing word");
        check(ydpdict_close(dict) == 0, "close dictionary");
    }
    check(remove(dat) == 0, "remove data file");
    check(remove(idx) == 0, "remove index file");
    printf("consumer e2e: %s\n", failures ? "FAILED" : "OK (13 checks)");
    return failures ? 1 : 0;
}
