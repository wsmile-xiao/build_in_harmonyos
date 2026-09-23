#include <menu.h>

#include <stdio.h>
#include <string.h>

/* Consumer assertions for the packaged libmenuw against the ncurses core.
 * Each guarded block is one assertion site; the full pass prints
 * "MENU_CONSUMER_OK passed=16/16" to the output file and exits 0.
 * endwin()/delscreen() after newterm() on plain FILE streams perform cleanup
 * but their return value is not a reliable assertion on this platform, so
 * they are called without a return check (matching upstream test practice). */

static int fail(const char *message) {
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv) {
    FILE *output;
    FILE *input;
    SCREEN *screen;
    const char *names[3] = {"alpha", "beta", "gamma"};
    const char *descriptions[3] = {"first entry", "second entry", "third entry"};
    ITEM *items[4];
    MENU *menu;
    int rows;
    int cols;
    int index;
    int marker;

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

    /* 1. item creation and name/description round trip */
    for (index = 0; index < 3; ++index) {
        items[index] = new_item(names[index], descriptions[index]);
    }
    items[3] = (ITEM *)0;
    if (items[0] == NULL || items[1] == NULL || items[2] == NULL ||
        strcmp(item_name(items[0]), "alpha") != 0 ||
        strcmp(item_description(items[1]), "second entry") != 0) {
        return fail("new_item and item_name/item_description");
    }

    /* 2. menu creation over the item vector and item_count */
    menu = new_menu(items);
    if (menu == NULL || item_count(menu) != 3) {
        return fail("new_menu and item_count");
    }

    /* 3. default menu options: single value, row-major, non-cyclic */
    if ((menu_opts(menu) & (O_ONEVALUE | O_ROWMAJOR | O_NONCYCLIC)) !=
        (O_ONEVALUE | O_ROWMAJOR | O_NONCYCLIC)) {
        return fail("default O_ONEVALUE/O_ROWMAJOR/O_NONCYCLIC menu options");
    }

    /* 4. menu mark round trip */
    if (set_menu_mark(menu, "*") != E_OK ||
        strcmp(menu_mark(menu), "*") != 0) {
        return fail("set_menu_mark and menu_mark");
    }

    /* 5. foreground and background display attributes */
    if (set_menu_fore(menu, A_REVERSE) != E_OK ||
        menu_fore(menu) != A_REVERSE ||
        set_menu_back(menu, A_NORMAL) != E_OK ||
        menu_back(menu) != A_NORMAL) {
        return fail("set_menu_fore/menu_fore and set_menu_back/menu_back");
    }

    /* 6. fill character round trip */
    if (set_menu_pad(menu, '-') != E_OK || menu_pad(menu) != '-') {
        return fail("set_menu_pad and menu_pad");
    }

    /* 7. item user pointer round trip */
    marker = 7;
    if (set_item_userptr(items[1], &marker) != E_OK ||
        item_userptr(items[1]) != &marker) {
        return fail("set_item_userptr and item_userptr");
    }

    /* 8. item value toggle (programmatically allowed only for
     *    multi-valued menus, so O_ONEVALUE is dropped and restored) */
    if (menu_opts_off(menu, O_ONEVALUE) != E_OK ||
        set_item_value(items[2], TRUE) != E_OK ||
        item_value(items[2]) == FALSE ||
        menu_opts_on(menu, O_ONEVALUE) != E_OK) {
        return fail("menu_opts_off, set_item_value and item_value");
    }

    /* 9. selectable item option off/on round trip */
    if (item_opts_off(items[0], O_SELECTABLE) != E_OK ||
        (item_opts(items[0]) & O_SELECTABLE) != 0 ||
        item_opts_on(items[0], O_SELECTABLE) != E_OK ||
        (item_opts(items[0]) & O_SELECTABLE) == 0) {
        return fail("item_opts_off and item_opts_on");
    }

    /* 10. scale_menu reports the window size; with the default format the
     *     three items occupy three rows of one column */
    if (scale_menu(menu, &rows, &cols) != E_OK ||
        rows != 3 || cols < 1) {
        return fail("scale_menu minimum geometry");
    }

    /* 11. set_menu_format constrains the item rows (two rows per column for
     *     three items); scale_menu mirrors the reduced height */
    if (set_menu_format(menu, 2, 2) != E_OK ||
        scale_menu(menu, &rows, &cols) != E_OK ||
        rows != 2 || cols < 1) {
        return fail("set_menu_format and scaled geometry");
    }

    /* 12. posting selects the first item, positions the cursor, and makes
     *     items visible */
    if (post_menu(menu) != E_OK ||
        current_item(menu) != items[0] ||
        item_index(current_item(menu)) != 0 ||
        pos_menu_cursor(menu) != E_OK ||
        item_visible(items[0]) == FALSE) {
        return fail("post_menu, current_item, pos_menu_cursor and item_visible");
    }

    /* 13. jump to the last item; the default non-cyclic next is denied and
     *     in-bounds prev/next navigation works (option changes are only
     *     allowed on an unposted menu, so this block is driver-only) */
    if (menu_driver(menu, REQ_LAST_ITEM) != E_OK ||
        item_index(current_item(menu)) != 2 ||
        menu_driver(menu, REQ_NEXT_ITEM) != E_REQUEST_DENIED ||
        menu_driver(menu, REQ_PREV_ITEM) != E_OK ||
        item_index(current_item(menu)) != 1 ||
        menu_driver(menu, REQ_NEXT_ITEM) != E_OK ||
        item_index(current_item(menu)) != 2) {
        return fail("REQ_LAST_ITEM, denied REQ_NEXT_ITEM and REQ_PREV_ITEM");
    }

    /* 14. explicit selection and in-bounds row-major navigation */
    if (set_current_item(menu, items[2]) != E_OK ||
        item_index(current_item(menu)) != 2 ||
        menu_driver(menu, REQ_UP_ITEM) != E_OK ||
        item_index(current_item(menu)) != 0 ||
        menu_driver(menu, REQ_RIGHT_ITEM) != E_OK ||
        item_index(current_item(menu)) != 1 ||
        menu_driver(menu, REQ_LEFT_ITEM) != E_OK ||
        item_index(current_item(menu)) != 0) {
        return fail("set_current_item and row-major driver navigation");
    }

    /* 15. request name tables round trip */
    if (strcmp(menu_request_name(REQ_NEXT_ITEM), "NEXT_ITEM") != 0 ||
        menu_request_by_name("PREV_ITEM") != REQ_PREV_ITEM) {
        return fail("menu_request_name and menu_request_by_name");
    }

    /* 16. unpost and full teardown */
    if (unpost_menu(menu) != E_OK ||
        free_menu(menu) != E_OK ||
        free_item(items[0]) != E_OK ||
        free_item(items[1]) != E_OK ||
        free_item(items[2]) != E_OK) {
        return fail("unpost_menu, free_menu and free_item lifecycle");
    }

    /* terminal teardown (cleanup only, see file comment) */
    endwin();
    delscreen(screen);

    fprintf(output, "MENU_CONSUMER_OK passed=16/16\n");
    fflush(output);
    fclose(output);
    fclose(input);
    return 0;
}
