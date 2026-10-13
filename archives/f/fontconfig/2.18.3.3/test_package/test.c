#include <fontconfig/fontconfig.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    FcConfig *config;
    FcPattern *pattern = NULL, *match = NULL;
    FcFontSet *fonts;
    FcChar8 *filename = NULL;
    FcResult result = FcResultNoMatch;
    FILE *file;
    int rc = 1;
    if (argc != 3) return 2;
    config = FcConfigCreate();
    if (!config) return 3;
    if (!strcmp(argv[2], "reject")) {
        rc = FcConfigParseAndLoad(config, (const FcChar8 *)argv[1], FcTrue) ? 4 : 0;
        printf("CONFIG_REJECTION %s\n", rc ? "FAIL" : "PASS");
        FcConfigDestroy(config);
        return rc;
    }
    if (!FcConfigParseAndLoad(config, (const FcChar8 *)argv[1], FcTrue)) goto done;
    if (!FcConfigBuildFonts(config)) goto done;
    fonts = FcConfigGetFonts(config, FcSetSystem);
    if (!fonts || fonts->nfont <= 0) goto done;
    pattern = FcNameParse((const FcChar8 *)"sans-serif");
    if (!pattern || !FcConfigSubstitute(config, pattern, FcMatchPattern)) goto done;
    FcDefaultSubstitute(pattern);
    match = FcFontMatch(config, pattern, &result);
    if (!match || result != FcResultMatch) goto done;
    if (FcPatternGetString(match, FC_FILE, 0, &filename) != FcResultMatch) goto done;
    file = fopen((const char *)filename, "rb");
    if (!file) goto done;
    if (fclose(file)) goto done;
    printf("CONFIG_LOAD PASS\nFONT_ENUMERATION PASS count=%d\nFONT_MATCH PASS file=%s\n",
           fonts->nfont, (const char *)filename);
    rc = 0;
done:
    if (match) FcPatternDestroy(match);
    if (pattern) FcPatternDestroy(pattern);
    FcConfigDestroy(config);
    if (rc) fprintf(stderr, "Font configuration/discovery/matching FAILED\n");
    return rc;
}
