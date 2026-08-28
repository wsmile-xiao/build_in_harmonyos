#include <stdio.h>
#include <string.h>
#include <X11/Xft/Xft.h>

#define CHECK_TRUE(value, code) \
    do { \
        if (!(value)) { \
            return (code); \
        } \
    } while (0)

int main(void)
{
    FcPattern *name_pattern;
    FcPattern *xlfd_pattern;
    FcPattern *invalid_pattern;
    FcChar8 *family = NULL;
    double size = 0.0;
    char name_buffer[512] = {0};
    char xlfd_buffer[512] = {0};

    CHECK_TRUE(XftInitFtLibrary(), 1);

    name_pattern = XftNameParse("sans-12:style=Regular");
    CHECK_TRUE(name_pattern != NULL, 2);
    CHECK_TRUE(XftNameUnparse(name_pattern, name_buffer, sizeof(name_buffer)), 3);
    CHECK_TRUE(name_buffer[0] != '\0', 4);
    CHECK_TRUE(
        FcPatternGetString(name_pattern, FC_FAMILY, 0, &family) == FcResultMatch,
        5
    );
    CHECK_TRUE(family != NULL, 6);
    CHECK_TRUE(strcmp((const char *)family, "sans") == 0, 7);
    CHECK_TRUE(
        FcPatternGetDouble(name_pattern, FC_SIZE, 0, &size) == FcResultMatch,
        8
    );
    CHECK_TRUE(size == 12.0, 9);

    xlfd_pattern = XftXlfdParse(
        "-misc-fixed-medium-r-normal--13-120-75-75-c-70-iso10646-1",
        FcFalse,
        FcTrue
    );
    CHECK_TRUE(xlfd_pattern != NULL, 10);
    family = NULL;
    CHECK_TRUE(
        FcPatternGetString(xlfd_pattern, FC_FAMILY, 0, &family) == FcResultMatch,
        11
    );
    CHECK_TRUE(family != NULL, 12);
    CHECK_TRUE(strcmp((const char *)family, "fixed") == 0, 13);

    invalid_pattern = XftXlfdParse("invalid", FcFalse, FcTrue);
    CHECK_TRUE(invalid_pattern == NULL, 14);
    CHECK_TRUE(XftNameUnparse(xlfd_pattern, xlfd_buffer, sizeof(xlfd_buffer)), 15);
    CHECK_TRUE(xlfd_buffer[0] != '\0', 16);

    FcPatternDestroy(xlfd_pattern);
    FcPatternDestroy(name_pattern);
    puts("LIBXFT_NAME_CONTRACT_PASS assertions=16");
    return 0;
}
