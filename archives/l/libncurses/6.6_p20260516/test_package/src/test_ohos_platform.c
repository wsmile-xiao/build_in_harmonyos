/*
 * HarmonyOS-specific platform contract for libncurses 6.6_p20260516.
 *
 * The narrow ncurses static package exists on HarmonyOS PC so that consumers
 * can use the 8-bit ABI without touching the wide shared curses library that
 * the platform shell depends on.  This program therefore verifies the two
 * properties that are only observable on a HarmonyOS target:
 *
 *   1. the process really runs on HarmonyOS;
 *   2. the linked curses implementation is the statically packaged narrow
 *      archive and no shared curses/tinfo object is mapped into the process,
 *      so the package cannot shadow a platform libncurses/libtinfo.
 */
#include <curses.h>
#include <term.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>

static int fail(const char *message) {
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static int discard_character(int value) {
    return value;
}

static int platform_is_harmonyos(void) {
    struct utsname information;

    if (uname(&information) != 0) {
        return 0;
    }
    return strstr(information.sysname, "HarmonyOS") != NULL;
}

static int shared_curses_is_mapped(void) {
    static const char *const names[] = {
        "libncurses.so", "libncursesw.so", "libtinfo.so", "libtinfow.so",
        "libform.so", "libformw.so", "libmenu.so", "libmenuw.so",
        "libpanel.so", "libpanelw.so",
    };
    char line[4096];
    FILE *maps = fopen("/proc/self/maps", "r");
    size_t index;

    if (maps == NULL) {
        return -1;
    }
    while (fgets(line, sizeof(line), maps) != NULL) {
        for (index = 0; index < sizeof(names) / sizeof(names[0]); ++index) {
            if (strstr(line, names[index]) != NULL) {
                fclose(maps);
                return 1;
            }
        }
    }
    fclose(maps);
    return 0;
}

int main(int argc, char **argv) {
    FILE *output;
    FILE *input;
    SCREEN *screen;
    WINDOW *window;
    int mapped;
    int error = 0;

    if (argc != 3) {
        return fail("expected output and input paths");
    }
    if (!platform_is_harmonyos()) {
        return fail("harmonyos platform detection");
    }
    mapped = shared_curses_is_mapped();
    if (mapped != 0) {
        return fail("shared curses/tinfo library mapped into the process");
    }
    if (setupterm("xterm", 1, &error) != OK || error != 1 ||
        tputs(tigetstr("clear"), 1, discard_character) == ERR) {
        return fail("packaged terminfo database");
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
    window = newwin(1, 8, 0, 0);
    if (window == NULL || waddstr(window, "ohos") == ERR ||
        wrefresh(window) == ERR) {
        return fail("narrow window update on harmonyos");
    }
    delwin(window);
    endwin();
    delscreen(screen);
    fclose(input);
    fclose(output);

    puts("OHOS_PLATFORM_CONTRACT=4/4");
    return 0;
}
