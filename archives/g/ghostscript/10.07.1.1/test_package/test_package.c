#include <ghostscript/iapi.h>
#include <ghostscript/ierrors.h>

#include <stdio.h>
#include <string.h>

static int
png_ok(const char *path)
{
    FILE *file = fopen(path, "rb");
    unsigned char sig[8];
    const unsigned char png[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    long size;

    if (file == NULL) {
        fprintf(stderr, "missing render output %s\n", path);
        return 0;
    }
    if (fread(sig, 1, 8, file) != 8 || memcmp(sig, png, 8) != 0) {
        fprintf(stderr, "output is not a PNG: %s\n", path);
        fclose(file);
        return 0;
    }
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return 0;
    }
    size = ftell(file);
    fclose(file);
    if (size < 500) {
        fprintf(stderr, "PNG too small: %ld\n", size);
        return 0;
    }
    printf("PASS png bytes=%ld\n", size);
    return 1;
}

int
main(void)
{
    gsapi_revision_t revision;
    void *instance = NULL;
    int code;
    int exit_code;
    char *argv[] = {
        "gs",
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=png16m",
        "-r72",
        "-sOutputFile=libgs-page.png",
        "-c",
        "0.1 0.35 0.85 setrgbcolor 20 20 160 200 rectfill showpage"
    };

    code = gsapi_revision(&revision, (int)sizeof(revision));
    if (code != 0 || revision.revision <= 0) {
        fprintf(stderr, "gsapi_revision failed: %d\n", code);
        return 1;
    }
    printf("PASS 1/2 libgs revision=%ld product=%s\n",
           revision.revision, revision.product ? revision.product : "");

    code = gsapi_new_instance(&instance, NULL);
    if (code < 0 || instance == NULL) {
        fprintf(stderr, "gsapi_new_instance failed: %d\n", code);
        return 2;
    }
    gsapi_set_arg_encoding(instance, GS_ARG_ENCODING_UTF8);
    code = gsapi_init_with_args(instance, (int)(sizeof(argv) / sizeof(argv[0])), argv);
    exit_code = gsapi_exit(instance);
    if (code == 0 || code == gs_error_Quit)
        code = (exit_code == 0 || exit_code == gs_error_Quit) ? 0 : exit_code;
    gsapi_delete_instance(instance);
    if (code != 0 || !png_ok("libgs-page.png")) {
        fprintf(stderr, "libgs page render failed: %d\n", code);
        return 3;
    }
    printf("PASS 2/2 libgs rendered one page\n");
    return 0;
}
