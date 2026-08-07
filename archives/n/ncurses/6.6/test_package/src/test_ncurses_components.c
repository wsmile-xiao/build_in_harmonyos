#include <curses.h>
#include <form.h>
#include <menu.h>
#include <panel.h>

#include <stdio.h>
#include <string.h>

static int fail(const char *message) {
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv) {
    FILE *output;
    FILE *input;
    SCREEN *screen;
    WINDOW *window;
    PANEL *panel;
    ITEM *item;
    FIELD *field;

    if (argc != 3) {
        return fail("expected output and input paths");
    }
    output = fopen(argv[1], "w+");
    input = fopen(argv[2], "r");
    if (output == NULL || input == NULL) {
        return fail("open terminal streams");
    }
    screen = newterm("xterm", output, input);
    if (screen == NULL) {
        return fail("newterm with packaged terminfo");
    }
    set_term(screen);

    window = newwin(2, 16, 0, 0);
    panel = window == NULL ? NULL : new_panel(window);
    if (panel == NULL || panel_window(panel) != window ||
        hide_panel(panel) != OK || show_panel(panel) != OK) {
        return fail("panel lifecycle");
    }

    item = new_item("name", "description");
    if (item == NULL || strcmp(item_name(item), "name") != 0) {
        return fail("menu item lifecycle");
    }

    field = new_field(1, 16, 0, 0, 0, 0);
    if (field == NULL || set_field_buffer(field, 0, "value") != E_OK ||
        strncmp(field_buffer(field, 0), "value", 5) != 0) {
        return fail("form field lifecycle");
    }

    free_field(field);
    free_item(item);
    del_panel(panel);
    delwin(window);
    endwin();
    delscreen(screen);
    fclose(input);
    fclose(output);

    puts("NCURSES_COMPONENTS=3/3");
    return 0;
}
