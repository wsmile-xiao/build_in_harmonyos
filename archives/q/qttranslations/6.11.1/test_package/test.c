#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check_file(const char *directory, const char *name)
{
    char filename[4096];
    FILE *file;
    long size;

    if (snprintf(filename, sizeof(filename), "%s/%s", directory, name) >= (int)sizeof(filename)) {
        fprintf(stderr, "path too long: %s\n", name);
        return 1;
    }

    file = fopen(filename, "rb");
    if (file == NULL) {
        fprintf(stderr, "cannot open: %s\n", filename);
        return 1;
    }

    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        fprintf(stderr, "cannot seek: %s\n", filename);
        return 1;
    }

    size = ftell(file);
    fclose(file);

    if (size <= 0) {
        fprintf(stderr, "empty file: %s\n", filename);
        return 1;
    }

    printf("OK: %s (%ld bytes)\n", filename, size);
    return 0;
}

int main(void)
{
    const char *directory = getenv("QT_TRANSLATIONS_PATH");
    const char *files[] = {
        "catalogs.json",
        "qt_zh_CN.qm",
        "qtbase_zh_CN.qm",
        "linguist_zh_CN.qm"
    };
    size_t index;

    if (directory == NULL || directory[0] == '\0') {
        fprintf(stderr, "QT_TRANSLATIONS_PATH is not set\n");
        return 1;
    }

    printf("QT_TRANSLATIONS_PATH=%s\n", directory);

    for (index = 0; index < sizeof(files) / sizeof(files[0]); ++index) {
        if (check_file(directory, files[index]) != 0) {
            return 1;
        }
    }

    return 0;
}
