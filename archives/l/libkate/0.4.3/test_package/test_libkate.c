#include <kate/kate.h>

#include <stdio.h>
#include <string.h>

int main(int argc, char** argv)
{
    kate_info info;
    int result = kate_info_init(&info);
    if (result != 0)
    {
        fprintf(stderr, "kate_info_init failed: %d\n", result);
        return 1;
    }

    if (argc == 2 && strcmp(argv[1], "--invalid-language") == 0)
    {
        result = kate_info_set_language(&info, "_");
        kate_info_clear(&info);
        if (result != KATE_E_INVALID_PARAMETER)
        {
            fprintf(stderr, "invalid language returned %d\n", result);
            return 2;
        }
        puts("invalid Kate language rejected");
        return 0;
    }
    if (argc != 1)
    {
        kate_info_clear(&info);
        fprintf(stderr, "usage: test_libkate [--invalid-language]\n");
        return 3;
    }

    if (strcmp(kate_get_version_string(), "libkate 0.4.3 (Tiger)") != 0)
    {
        kate_info_clear(&info);
        fprintf(stderr, "unexpected libkate version string\n");
        return 4;
    }
    if (kate_get_version() != 0x000403)
    {
        kate_info_clear(&info);
        fprintf(stderr, "unexpected libkate numeric version\n");
        return 5;
    }
    if (kate_info_set_language(&info, "en_GB") != 0)
    {
        kate_info_clear(&info);
        fprintf(stderr, "valid language was rejected\n");
        return 6;
    }
    if (kate_info_matches_language(&info, "en") != 2)
    {
        kate_info_clear(&info);
        fprintf(stderr, "language prefix match failed\n");
        return 7;
    }
    if (kate_info_set_category(&info, "subtitles") != 0)
    {
        kate_info_clear(&info);
        fprintf(stderr, "valid category was rejected\n");
        return 8;
    }
    if (kate_info_clear(&info) != 0)
    {
        fprintf(stderr, "kate_info_clear failed\n");
        return 9;
    }

    puts("libkate consumer checks passed");
    return 0;
}
