#include <allegro.h>

#include <errno.h>
#include <stdio.h>

int main(void)
{
    int color;

    if (install_allegro(SYSTEM_NONE, &errno, atexit) != 0) {
        fprintf(stderr, "install_allegro(SYSTEM_NONE) failed: %s\n", allegro_error);
        return 1;
    }

    color = makecol_depth(32, 0x12, 0x34, 0x56);
    if (getr_depth(32, color) != 0x12 ||
        getg_depth(32, color) != 0x34 ||
        getb_depth(32, color) != 0x56) {
        fprintf(stderr, "32-bit color round trip failed: %d\n", color);
        allegro_exit();
        return 1;
    }

    allegro_message("allegro core contract reached\n");
    allegro_exit();
    puts("allegro_core_contract PASS");
    return 0;
}
