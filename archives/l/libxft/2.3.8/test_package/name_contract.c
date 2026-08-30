#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include <X11/Xft/Xft.h>

#define CHECK_TRUE(value, code) \
    do { \
        if (!(value)) { \
            printf("LIBXFT_NAME_CONTRACT_FAIL code=%d\n", (code)); \
            return (code); \
        } \
    } while (0)

#define CHECK_STR(actual, expected, code) \
    do { \
        const char *observed_ = (actual); \
        CHECK_TRUE(observed_ != NULL, (code)); \
        CHECK_TRUE(strcmp(observed_, (expected)) == 0, (code) + 1); \
    } while (0)

static int
check_int(FcPattern *pattern, const char *object, int expected, int code)
{
    int value = -1;

    if (FcPatternGetInteger(pattern, object, 0, &value) != FcResultMatch) {
        return code;
    }
    if (value != expected) {
        return code + 1;
    }
    return 0;
}

static int
check_double(FcPattern *pattern, const char *object, double expected, int code)
{
    double value = 0.0;

    if (FcPatternGetDouble(pattern, object, 0, &value) != FcResultMatch) {
        return code;
    }
    if (value != expected) {
        return code + 1;
    }
    return 0;
}

int
main(void)
{
    FcPattern *name_pattern;
    FcPattern *xlfd_pattern;
    FcPattern *invalid_pattern;
    FcChar8 *family = NULL;
    FcChar8 *foundry = NULL;
    FcChar8 *style = NULL;
    FcChar8 *xlfd_object = NULL;
    char name_buffer[512];
    char xlfd_buffer[512];
    static const char xlfd_name[] =
        "-misc-fixed-medium-r-normal--13-120-75-75-c-70-iso10646-1";

    CHECK_TRUE(XftInitFtLibrary(), 1);

    /*
     * Fontconfig-style name contract: XftNameParse is the entry point every
     * XftFontOpenName call goes through before it touches a display.
     */
    memset(name_buffer, 0, sizeof(name_buffer));
    name_pattern = XftNameParse("sans-12:style=Regular");
    CHECK_TRUE(name_pattern != NULL, 2);
    CHECK_TRUE(
        FcPatternGetString(name_pattern, FC_FAMILY, 0, &family) == FcResultMatch,
        3
    );
    CHECK_STR((const char *) family, "sans", 4);
    CHECK_TRUE(
        FcPatternGetString(name_pattern, FC_STYLE, 0, &style) == FcResultMatch,
        6
    );
    CHECK_STR((const char *) style, "Regular", 7);
    CHECK_TRUE(check_double(name_pattern, FC_SIZE, 12.0, 9) == 0, 9);
    CHECK_TRUE(
        XftNameUnparse(name_pattern, name_buffer, sizeof(name_buffer)),
        11
    );
    CHECK_TRUE(name_buffer[0] != '\0', 12);
    CHECK_TRUE(strstr(name_buffer, "sans") != NULL, 13);

    /*
     * XLFD contract: field mapping, weight/slant tables and the preserved
     * raw name under the XFT_XLFD object.
     */
    memset(xlfd_buffer, 0, sizeof(xlfd_buffer));
    xlfd_pattern = XftXlfdParse(xlfd_name, FcFalse, FcTrue);
    CHECK_TRUE(xlfd_pattern != NULL, 14);
    CHECK_TRUE(
        FcPatternGetString(xlfd_pattern, FC_FAMILY, 0, &family) == FcResultMatch,
        15
    );
    CHECK_STR((const char *) family, "fixed", 16);
    CHECK_TRUE(
        FcPatternGetString(xlfd_pattern, FC_FOUNDRY, 0, &foundry) == FcResultMatch,
        18
    );
    CHECK_STR((const char *) foundry, "misc", 19);
    CHECK_TRUE(
        FcPatternGetString(xlfd_pattern, XFT_XLFD, 0, &xlfd_object)
            == FcResultMatch,
        21
    );
    CHECK_STR((const char *) xlfd_object, xlfd_name, 22);
    CHECK_TRUE(
        check_int(xlfd_pattern, FC_WEIGHT, FC_WEIGHT_MEDIUM, 24) == 0, 24
    );
    CHECK_TRUE(
        check_int(xlfd_pattern, FC_SLANT, FC_SLANT_ROMAN, 26) == 0, 26
    );
    CHECK_TRUE(check_double(xlfd_pattern, FC_SIZE, 12.0, 28) == 0, 28);
    CHECK_TRUE(check_double(xlfd_pattern, FC_PIXEL_SIZE, 13.0, 30) == 0, 30);
    CHECK_TRUE(
        XftNameUnparse(xlfd_pattern, xlfd_buffer, sizeof(xlfd_buffer)),
        32
    );
    CHECK_TRUE(xlfd_buffer[0] != '\0', 33);

    /*
     * Rejection contracts: every one of these must return NULL instead of a
     * partially populated pattern.
     */
    invalid_pattern = XftXlfdParse("invalid", FcFalse, FcTrue);
    CHECK_TRUE(invalid_pattern == NULL, 34);
    invalid_pattern = XftXlfdParse(
        "-misc-fixed-medium-r-normal", FcFalse, FcTrue
    );
    CHECK_TRUE(invalid_pattern == NULL, 35);
    invalid_pattern = XftXlfdParse(
        "-misc-fixed-medium-r-normal--0-120-75-75-c-70-iso10646-1",
        FcFalse,
        FcTrue
    );
    CHECK_TRUE(invalid_pattern == NULL, 36);
    invalid_pattern = XftXlfdParse(
        "-misc-fixed-medium-r-normal--13-120-75-75-c-70-iso10646-1-x",
        FcFalse,
        FcTrue
    );
    CHECK_TRUE(invalid_pattern == NULL, 37);
    invalid_pattern = XftXlfdParse("", FcFalse, FcTrue);
    CHECK_TRUE(invalid_pattern == NULL, 38);

    FcPatternDestroy(xlfd_pattern);
    FcPatternDestroy(name_pattern);
    puts("LIBXFT_NAME_CONTRACT_PASS assertions=28");
    return 0;
}
