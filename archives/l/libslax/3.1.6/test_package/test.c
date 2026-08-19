#include <stdio.h>
#include <libslax/slax.h>

int main(void)
{
    if (SLAX_VERSION_NUMBER <= 0) {
        fprintf(stderr, "invalid SLAX version\n");
        return 1;
    }

    slaxSetExitCode(17);

    if (slaxGetExitCode() != 17) {
        fprintf(stderr, "slax exit-code round-trip failed\n");
        return 1;
    }

    slaxSetExitCode(0);

    printf("libslax consumer probe ok: %s\n", SLAX_VERSION);
    return 0;
}
