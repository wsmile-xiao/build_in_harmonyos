/* test_libcli.c — libcli 1.10.7 consumer smoke test.
 *
 * Exercises the real libcli API headlessly (no sockets): init a CLI context,
 * register a parent/child command tree, run a command via cli_run_command(),
 * capture cli_print() output through a print callback, then unregister the
 * parent (cli_unregister_command only matches top-level names; children become
 * inaccessible per libcli.h) and verify the child no longer resolves. Each CHECK prints a TAP-style line;
 * any failure is counted and the program exits non-zero (R34: real API calls,
 * no shell-only test).
 */

#include <libcli.h>

#include <stdio.h>
#include <string.h>

static int check_no = 0;
static int failures = 0;

#define CHECK(cond, name)                                          \
    do {                                                           \
        check_no++;                                                \
        if (cond) {                                                \
            printf("ok %d - %s\n", check_no, name);                \
        } else {                                                   \
            printf("not ok %d - %s\n", check_no, name);            \
            failures++;                                            \
        }                                                          \
    } while (0)

static int cb_called = 0;
static int cb_argc = -1;

static int test_cb(struct cli_def *cli, const char *command, char *argv[], int argc) {
    (void)command;
    (void)argv;
    cb_called++;
    cb_argc = argc;
    cli_print(cli, "callback executed");
    return CLI_OK;
}

static char captured[4096];
static size_t captured_len = 0;

static void capture_print(struct cli_def *cli, const char *string) {
    size_t n;
    (void)cli;
    n = strlen(string);
    if (captured_len + n + 1 < sizeof(captured)) {
        memcpy(captured + captured_len, string, n);
        captured_len += n;
        captured[captured_len++] = '\n';
        captured[captured_len] = '\0';
    }
}

int main(void) {
    struct cli_def *cli;
    struct cli_command *c_show;
    struct cli_command *c_version;
    int rc;

    cli = cli_init();
    CHECK(cli != NULL, "cli_init returns non-NULL context");
    if (cli == NULL) {
        printf("1..1\n");
        return 1;
    }

    cli_print_callback(cli, capture_print);
    cli_set_banner(cli, "libcli test banner");
    cli_set_hostname(cli, "testhost");
    cli_set_promptchar(cli, "# ");
    cli_allow_user(cli, "fred", "nerk");

    c_show = cli_register_command(cli, NULL, "show", NULL, PRIVILEGE_UNPRIVILEGED, MODE_EXEC, "show tree");
    CHECK(c_show != NULL, "register parent command 'show'");

    c_version = cli_register_command(cli, c_show, "version", test_cb, PRIVILEGE_UNPRIVILEGED,
                                     MODE_EXEC, "show version");
    CHECK(c_version != NULL, "register child command 'show version'");

    rc = cli_run_command(cli, "show version");
    CHECK(rc == CLI_OK, "cli_run_command('show version') returns CLI_OK");

    CHECK(cb_called == 1, "command callback invoked exactly once");

    CHECK(cb_argc == 0, "callback argc is 0 for bare command");

    CHECK(strstr(captured, "callback executed") != NULL,
          "cli_print output captured via print callback");

    CHECK(cli_unregister_command(cli, "show") == CLI_OK, "unregister parent command 'show'");

    rc = cli_run_command(cli, "show version");
    CHECK(rc != CLI_OK, "unregistered tree no longer resolves");

    CHECK(cli_done(cli) == CLI_OK, "cli_done releases the context");

    printf("1..%d\n", check_no);
    if (failures == 0)
        printf("libcli smoke test passed (%d/%d)\n", check_no, check_no);
    return failures ? 1 : 0;
}
