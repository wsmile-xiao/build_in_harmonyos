/*
 * test_package consumer test — embedded-cli 0.1.4
 *
 * Real API consumer: creates a CLI via public API, binds a command,
 * feeds bytes through the public rx interface and asserts the binding
 * fires with the expected tokenized args (R34: not an empty shell test).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "embedded_cli.h"

static int binding_fired = 0;
static char captured_args[128] = {0};

static void on_led_binding(EmbeddedCli *cli, char *args, void *context) {
    (void)cli;
    (void)context;
    binding_fired = 1;
    if (args != NULL) {
        /* with tokenizeArgs=true the callback receives the tokenized string:
         * tokens are separated by single 0x00 and the list ends with 0x00 0x00.
         * Read tokens via the public token API. */
        snprintf(captured_args, sizeof(captured_args), "%s %s",
                 embeddedCliGetToken(args, 1), embeddedCliGetToken(args, 2));
    }
}

static void sink_write_char(EmbeddedCli *cli, char c) {
    (void)cli;
    (void)c;
}

int main(void) {
    EmbeddedCliConfig *config = embeddedCliDefaultConfig();
    if (config == NULL) {
        fprintf(stderr, "FAIL: embeddedCliDefaultConfig returned NULL\n");
        return 1;
    }

    EmbeddedCli *cli = embeddedCliNew(config);
    if (cli == NULL) {
        fprintf(stderr, "FAIL: embeddedCliNew returned NULL\n");
        return 1;
    }

    /* embeddedCliProcess() returns early while writeChar is NULL,
     * so a sink write callback is required for rx processing to run. */
    cli->writeChar = sink_write_char;
    cli->appContext = NULL;

    CliCommandBinding binding = {
        .name = "led",
        .help = "control the led: led <index> <0|1>",
        .tokenizeArgs = true,
        .context = NULL,
        .binding = on_led_binding,
    };
    if (!embeddedCliAddBinding(cli, binding)) {
        fprintf(stderr, "FAIL: embeddedCliAddBinding returned false\n");
        embeddedCliFree(cli);
        return 1;
    }

    /* feed "led 1 1\r\n" through the public rx interface */
    const char *input = "led 1 1\r\n";
    for (const char *p = input; *p; ++p) {
        embeddedCliReceiveChar(cli, *p);
        embeddedCliProcess(cli);
    }

    if (!binding_fired) {
        fprintf(stderr, "FAIL: binding callback was not fired\n");
        embeddedCliFree(cli);
        return 1;
    }
    if (strcmp(captured_args, "1 1") != 0) {
        fprintf(stderr, "FAIL: unexpected args '%s' (expected '1 1')\n", captured_args);
        embeddedCliFree(cli);
        return 1;
    }

    embeddedCliFree(cli);
    printf("PASS: embedded-cli binding fired with args='%s'\n", captured_args);
    return 0;
}
