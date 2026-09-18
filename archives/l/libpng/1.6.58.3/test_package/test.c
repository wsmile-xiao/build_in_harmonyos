#include <png.h>
#include <stdio.h>

int main(void)
{
    const png_uint_32 runtime_version = png_access_version_number();
    const char *version_text = png_get_libpng_ver(NULL);

    if (runtime_version != PNG_LIBPNG_VER) {
        fprintf(stderr, "version mismatch: runtime=%lu headers=%d\n",
                (unsigned long)runtime_version, PNG_LIBPNG_VER);
        return 1;
    }
    if (version_text == NULL || version_text[0] == '\0') {
        fprintf(stderr, "png_get_libpng_ver returned an empty version\n");
        return 2;
    }
    printf("libpng runtime version: %s\n", version_text);
    return 0;
}
