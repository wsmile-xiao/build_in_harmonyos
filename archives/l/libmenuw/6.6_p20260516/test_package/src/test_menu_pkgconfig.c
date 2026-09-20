#include <curses.h>
#include <menu.h>

/* Minimal pkg-config linked consumer: forces menu and curses core symbols
 * so the -Wl,-t link trace must select the packaged static archives. */

int main(void) {
    SCREEN *screen;
    ITEM *items[3];
    MENU *menu;
    int code = 1;

    screen = newterm("xterm", stdout, stdin);
    if (screen == NULL) {
        return 2;
    }
    items[0] = new_item("one", "first");
    items[1] = new_item("two", "second");
    items[2] = (ITEM *)0;
    menu = items[0] == NULL || items[1] == NULL ? (MENU *)0 : new_menu(items);
    if (menu != (MENU *)0) {
        if (post_menu(menu) == E_OK &&
            menu_driver(menu, REQ_LAST_ITEM) == E_OK &&
            unpost_menu(menu) == E_OK) {
            code = 0;
        }
    }
    endwin();
    delscreen(screen);
    if (menu != (MENU *)0) {
        free_menu(menu);
    }
    if (items[0] != (ITEM *)0) {
        free_item(items[0]);
    }
    if (items[1] != (ITEM *)0) {
        free_item(items[1]);
    }
    return code;
}
