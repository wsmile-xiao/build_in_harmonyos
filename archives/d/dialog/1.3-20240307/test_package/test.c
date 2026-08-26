/* test_dialog.c — test_package for dialog 1.3-20240307
 *
 * Calls dialog_version() from libdialog.a by declaring the prototype
 * locally — avoids including dialog.h which pulls in curses.h from
 * the ncurses package (CMakeDeps include dir propagation issue).
 * Links against libdialog.a which itself links ncurses statically.
 */
#include <stdio.h>

extern const char *dialog_version(void);

int main(void)
{
    const char *ver = dialog_version();
    if (ver) {
        printf("dialog version: %s\n", ver);
        return 0;
    }
    fprintf(stderr, "dialog_version() returned NULL\n");
    return 1;
}
