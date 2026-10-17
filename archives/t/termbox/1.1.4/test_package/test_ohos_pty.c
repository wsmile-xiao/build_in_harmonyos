#define _XOPEN_SOURCE 600

#ifndef __OHOS__
#error "test_ohos_pty must be compiled for HarmonyOS"
#endif

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/utsname.h>
#include <termios.h>
#include <unistd.h>

#include <termbox.h>

static int checks;
static int failures;

static void check(int condition, const char *message)
{
    ++checks;
    if (!condition) {
        ++failures;
        fprintf(stderr, "FAIL: %s (errno=%d: %s)\n",
                message, errno, strerror(errno));
    }
}

int main(void)
{
    struct winsize size = {0};
    struct utsname system_info;
    struct tb_event event;
    struct tb_cell *cells;
    char *slave_name;
    int master_fd = -1;
    int slave_fd;
    int initialized = 0;
    int result;

    check(uname(&system_info) == 0, "uname succeeds on HarmonyOS");
    check(strcmp(system_info.machine, "aarch64") == 0,
          "HarmonyOS device architecture is aarch64");

    master_fd = posix_openpt(O_RDWR | O_NOCTTY);
    check(master_fd >= 0, "posix_openpt creates a PTY master");
    if (master_fd < 0)
        goto done;

    check(grantpt(master_fd) == 0, "grantpt succeeds");
    check(unlockpt(master_fd) == 0, "unlockpt succeeds");
    slave_name = ptsname(master_fd);
    check(slave_name != NULL, "ptsname returns a slave path");
    if (slave_name == NULL)
        goto done;

    slave_fd = open(slave_name, O_RDWR | O_NOCTTY);
    check(slave_fd >= 0, "PTY slave opens");
    if (slave_fd < 0)
        goto done;

    size.ws_col = 93;
    size.ws_row = 31;
    check(ioctl(slave_fd, TIOCSWINSZ, &size) == 0,
          "TIOCSWINSZ configures the PTY");
    check(setenv("TERM", "xterm", 1) == 0, "TERM is set to a built-in terminal");

    result = tb_init_fd(slave_fd);
    check(result == 0, "tb_init_fd initializes termbox on a HarmonyOS PTY");
    if (result != 0) {
        close(slave_fd);
        goto done;
    }
    initialized = 1;

    check(tb_width() == 93 && tb_height() == 31,
          "termbox reads the PTY window size");
    check(tb_select_input_mode(TB_INPUT_ALT) == TB_INPUT_ALT,
          "alternate input mode is selectable");
    check(tb_select_output_mode(TB_OUTPUT_256) == TB_OUTPUT_256,
          "256-color output mode is selectable");

    tb_set_clear_attributes(TB_WHITE, TB_BLUE);
    tb_clear();
    cells = tb_cell_buffer();
    check(cells != NULL && cells[0].ch == ' ' &&
              cells[0].fg == TB_WHITE && cells[0].bg == TB_BLUE,
          "clear attributes reach the terminal back buffer");
    tb_change_cell(0, 0, 'H', TB_GREEN | TB_BOLD, TB_DEFAULT);
    tb_present();
    check(cells[0].ch == 'H', "cell update survives presentation");

    check(raise(SIGWINCH) == 0, "SIGWINCH is delivered");
    result = tb_peek_event(&event, 1000);
    check(result == TB_EVENT_RESIZE && event.w == 93 && event.h == 31,
          "SIGWINCH produces a resize event with PTY dimensions");

done:
    if (initialized)
        tb_shutdown();
    if (master_fd >= 0)
        close(master_fd);

    if (failures != 0) {
        fprintf(stderr, "termbox OHOS PTY: %d/%d checks failed\n",
                failures, checks);
        return 1;
    }

    printf("termbox OHOS PTY: PASS (%d assertions)\n", checks);
    return 0;
}
