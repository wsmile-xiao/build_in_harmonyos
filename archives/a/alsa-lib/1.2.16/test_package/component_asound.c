#ifdef CHECK_DSO_PATH
#define _GNU_SOURCE
#endif

#include <alsa/asoundlib.h>

#ifdef CHECK_DSO_PATH
#include <dlfcn.h>
#endif
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    const char *actual = snd_asoundlib_version();
#ifdef CHECK_DSO_PATH
    Dl_info information = {0};
#endif

    if (argc != 3 || actual == NULL || strcmp(actual, argv[1]) != 0) {
        fprintf(stderr, "libasound version mismatch: expected=%s actual=%s\n",
                argc >= 2 ? argv[1] : "<missing>",
                actual == NULL ? "<null>" : actual);
        return 1;
    }
    if (strcmp(argv[2], "-") != 0) {
#ifdef CHECK_DSO_PATH
        if (dladdr((const void *)&snd_asoundlib_version, &information) == 0 ||
            information.dli_fname == NULL ||
            strstr(information.dli_fname, argv[2]) == NULL) {
            fprintf(stderr, "libasound loaded outside %s: %s\n",
                    argv[2],
                    information.dli_fname == NULL ?
                        "<unknown>" : information.dli_fname);
            return 1;
        }
#else
        fputs("shared-library path check was not compiled\n", stderr);
        return 1;
#endif
    }
    printf("libasound component version %s\n", actual);
    return 0;
}
