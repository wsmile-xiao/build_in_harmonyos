/*
 * SONAME and versioned-alias loader contract.
 *
 * This consumer deliberately does NOT link against libXft: every entry point
 * below is resolved through dlopen, so a failure means the shared object or
 * one of its versioned aliases cannot actually be loaded by the OHOS runtime
 * loader (file existence and `ls -l` are not accepted as evidence).
 */

#include <dlfcn.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include <fontconfig/fontconfig.h>

#define CHECK_TRUE(value, code) \
    do { \
        if (!(value)) { \
            printf("LIBXFT_SONAME_CONTRACT_FAIL code=%d detail=%s\n", \
                   (code), dlerror()); \
            return (code); \
        } \
    } while (0)

typedef int (*XftGetVersionFunc)(void);
typedef FcBool (*XftInitFtLibraryFunc)(void);
typedef FcPattern *(*XftNameParseFunc)(const char *name);
typedef FcBool (*XftNameUnparseFunc)(FcPattern *pat, char *dest, int len);

static int
probe_library(const char *library_name)
{
    void *handle;
    XftGetVersionFunc get_version;
    XftInitFtLibraryFunc init_ft_library;
    XftNameParseFunc name_parse;
    XftNameUnparseFunc name_unparse;
    FcPattern *pattern;
    FcChar8 *family = NULL;
    char buffer[256];

    (void) dlerror();
    handle = dlopen(library_name, RTLD_NOW | RTLD_LOCAL);
    CHECK_TRUE(handle != NULL, 1);

    get_version = (XftGetVersionFunc) dlsym(handle, "XftGetVersion");
    CHECK_TRUE(get_version != NULL, 2);
    CHECK_TRUE(get_version() == 20308, 3);

    init_ft_library =
        (XftInitFtLibraryFunc) dlsym(handle, "XftInitFtLibrary");
    CHECK_TRUE(init_ft_library != NULL, 4);
    CHECK_TRUE(init_ft_library(), 5);

    name_parse = (XftNameParseFunc) dlsym(handle, "XftNameParse");
    CHECK_TRUE(name_parse != NULL, 6);
    pattern = name_parse("fixed-10");
    CHECK_TRUE(pattern != NULL, 7);

    name_unparse = (XftNameUnparseFunc) dlsym(handle, "XftNameUnparse");
    CHECK_TRUE(name_unparse != NULL, 8);
    memset(buffer, 0, sizeof(buffer));
    CHECK_TRUE(name_unparse(pattern, buffer, sizeof(buffer)), 9);
    CHECK_TRUE(
        FcPatternGetString(pattern, FC_FAMILY, 0, &family) == FcResultMatch,
        10
    );
    CHECK_TRUE(family != NULL && strcmp((const char *) family, "fixed") == 0, 11);

    FcPatternDestroy(pattern);
    /* A display-bound entry point must still be exported by the loaded object. */
    CHECK_TRUE(dlsym(handle, "XftFontOpenName") != NULL, 12);
    CHECK_TRUE(dlclose(handle) == 0, 13);
    return 0;
}

int
main(void)
{
    /* Every name the package installs must be loadable, not only the SONAME. */
    CHECK_TRUE(probe_library("libXft.so.2") == 0, 100);
    CHECK_TRUE(probe_library("libXft.so") == 0, 200);

    puts("LIBXFT_SONAME_CONTRACT_PASS libraries=2 assertions=28");
    return 0;
}
