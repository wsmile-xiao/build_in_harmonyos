// Consumer verification for pdcurses/3.9 SDL2 flavour (R34).
// Real behavioural assertions against the curses API: draw + refresh +
// non-blocking input timeout + teardown. Headless execution requires the
// SDL dummy video driver (SDL_VIDEODRIVER=dummy), set by the runner.
#include <curses.h>

int main(void) {
    WINDOW *w = initscr();
    if (w == NULL) {
        return 2; /* curses subsystem failed to initialise */
    }

    /* Drawing API must accept formatted output. */
    if (printw("pdcurses-consumer-ok %d", 42) == ERR) {
        endwin();
        return 3;
    }
    refresh();

    /* Non-blocking input: with no terminal input available the call must
       return ERR after the timeout expires. */
    timeout(0);
    if (getch() != ERR) {
        endwin();
        return 4;
    }

    if (endwin() == ERR) {
        return 5;
    }
    return 0;
}
