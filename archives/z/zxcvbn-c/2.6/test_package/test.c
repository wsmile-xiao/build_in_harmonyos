#include <stdio.h>

#include <zxcvbn.h>

int main(void)
{
    const char *user_dictionary[] = {"example.com", "alice", NULL};
    ZxcMatch_t *info = NULL;
    double entropy = ZxcvbnMatch("password", user_dictionary, &info);

    if (!(entropy > 0.0) || info == NULL) {
        fprintf(stderr, "zxcvbn returned no useful match information\n");
        return 1;
    }

    if (info->Length <= 0) {
        fprintf(stderr, "zxcvbn returned an invalid match length\n");
        ZxcvbnFreeInfo(info);
        return 2;
    }

    ZxcvbnFreeInfo(info);
    if (!(ZxcvbnMatch("correct horse battery staple", NULL, NULL) > entropy)) {
        fprintf(stderr, "expected a longer password to have higher entropy\n");
        return 3;
    }

    puts("zxcvbn-c API smoke test passed");
    return 0;
}
