/* test_package consumer test for commander 1.4.0.
 * Simulates a business upper-layer CLI component: it parses a real command
 * line with commander, acts on the parsed options and prints observable
 * results. Only uses the installed public header + linked libcommander.a.
 * R34: genuinely depends on the tested package's API.
 */
#include <stdio.h>
#include <string.h>

#include "commander.h"

static void
verbose(command_t *self) {
  (void) self;
  printf("log-level: verbose\n");
}

static void
output(command_t *self) {
  printf("output-file: %s\n", self->arg ? self->arg : "(none)");
}

static void
repeat(command_t *self) {
  printf("repeat-count: %s\n", self->arg ? self->arg : "1");
}

int
main(int argc, char **argv) {
  command_t cmd;
  int i;

  command_init(&cmd, "consumer-cli", "1.0.0");
  command_option(&cmd, "-v", "--verbose", "enable verbose logging", verbose);
  command_option(&cmd, "-o", "--output <file>", "output file", output);
  command_option(&cmd, "-n", "--repeat [n]", "repeat count", repeat);
  command_parse(&cmd, argc, argv);

  printf("positional args (%d):\n", cmd.argc);
  for (i = 0; i < cmd.argc; ++i)
    printf("  %d: %s\n", i + 1, cmd.argv[i]);

  command_free(&cmd);
  printf("consumer-cli: OK\n");
  return 0;
}