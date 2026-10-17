#include <stdio.h>
#include <string.h>

#include <schrift.h>

int main(void)
{
    const char invalid_font[] = "not a TrueType font";

    if (strcmp(sft_version(), "0.10.2") != 0) {
        fprintf(stderr, "unexpected version: %s\n", sft_version());
        return 1;
    }

    if (sft_loadmem(invalid_font, sizeof(invalid_font)) != NULL) {
        fprintf(stderr, "invalid font data was accepted\n");
        return 1;
    }

    if (sft_loadfile("missing-font.ttf") != NULL) {
        fprintf(stderr, "missing font file was accepted\n");
        return 1;
    }

    printf("libschrift %s API checks passed\n", sft_version());
    return 0;
}
