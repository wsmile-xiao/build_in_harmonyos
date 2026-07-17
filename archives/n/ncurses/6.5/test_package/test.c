#include <stdio.h>
#include <curses.h>

int main(void) {
    const char *version = curses_version();
    if (version == NULL) {
        return 1;
    }
    printf("ncurses: %s\n", version);
    return 0;
}
