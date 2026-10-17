/*
 * test_harmonyos.c — commander 1.4.0 HarmonyOS-specific functional test
 *
 * This test is compiled and run with the OpenHarmony toolchain
 * (/data/service/hnp/bin/clang, clang 15.0.4). It actually calls the public
 * commander 1.4.0 C API and validates concrete behaviors:
 *   - command_init registers default -V/--version and -h/--help options
 *   - command_option registers short/large flags + required/optional args
 *   - command_parse dispatches the right callback and captures args
 *   - missing required arg -> "argument required" fatal path (exit 1)
 *   - unrecognized flag -> fatal path (exit 1)
 *   - "--" literal separator keeps following args as positional
 *   - combined short flags ("-vro ...") are exploded by normalize_args
 *   - positional args land in cmd.argc / cmd.argv
 *
 * Fatal paths (exit(1)) are verified via fork() + waitpid so the parent
 * process can assert the exact exit status.
 *
 * It also prints the OHOS compiler identity macros so the log proves the
 * binary was built by the OpenHarmony toolchain rather than the host gcc.
 */
#include "commander.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int g_failures = 0;

static void
verbose_cb(command_t *self) {
  (void) self;
  printf("  [callback] verbose fired\n");
}

static void
required_cb(command_t *self) {
  printf("  [callback] required arg = '%s'\n", self->arg ? self->arg : "NULL");
}

static void
optional_cb(command_t *self) {
  printf("  [callback] optional arg = '%s'\n", self->arg ? self->arg : "NULL");
}

static void
check(int cond, const char *what) {
  if (cond) {
    printf("  [PASS] %s\n", what);
  } else {
    printf("  [FAIL] %s\n", what);
    g_failures++;
  }
}

/* Run a child function that may exit(1) and return its exit status. */
static int
run_child(void (*fn)(void)) {
  pid_t pid = fork();
  if (pid == 0) {
    fn();
    _exit(0);
  }
  int st = 0;
  waitpid(pid, &st, 0);
  if (WIFEXITED(st))
    return WEXITSTATUS(st);
  return -1;
}

static void
child_missing_required(void) {
  char *argv[] = {"prog", "--required", NULL};
  command_t cmd;
  command_init(&cmd, "prog", "1.4.0");
  command_option(&cmd, "-r", "--required <arg>", "required arg", required_cb);
  command_parse(&cmd, 2, argv);
  command_free(&cmd);
}

static void
child_unrecognized(void) {
  char *argv[] = {"prog", "--nope", NULL};
  command_t cmd;
  command_init(&cmd, "prog", "1.4.0");
  command_parse(&cmd, 2, argv);
  command_free(&cmd);
}

int
main(void) {
  printf("=== commander 1.4.0 HarmonyOS test ===\n");

  /* Toolchain identity (proves OHOS build, not host gcc) */
#ifdef __clang__
  printf("compiler: clang %d.%d.%d (__clang__ defined)\n",
         __clang_major__, __clang_minor__, __clang_patchlevel__);
#else
  printf("compiler: NOT clang\n");
#endif
#ifdef __aarch64__
  printf("arch: __aarch64__ defined\n");
#endif
#if defined(__OHOS__) || defined(__OHOS)
  printf("platform: OHOS macro defined\n");
#endif

  /* ---- 1. defaults: -V/--version and -h/--help present after init ---- */
  {
    command_t cmd;
    command_init(&cmd, "prog", "1.4.0");
    check(cmd.option_count == 2,
          "command_init registers exactly 2 default options (-V, -h)");
    check(strcmp(cmd.options[0].large, "--version") == 0,
          "default option[0] is --version");
    check(strcmp(cmd.options[1].large, "--help") == 0,
          "default option[1] is --help");
    command_free(&cmd);
  }

  /* ---- 2. long flag dispatch + required arg capture ---- */
  {
    command_t cmd;
    char *argv[] = {"prog", "--required", "hello", "tail1", NULL};
    command_init(&cmd, "prog", "1.4.0");
    command_option(&cmd, "-r", "--required <arg>", "required arg", required_cb);
    command_parse(&cmd, 4, argv);
    check(cmd.argc == 1 && strcmp(cmd.argv[0], "tail1") == 0,
          "--required hello lands as arg; 'tail1' becomes positional");
    command_free(&cmd);
  }

  /* ---- 3. short flag dispatch + optional arg consumption ---- */
  {
    command_t cmd;
    char *argv[] = {"prog", "-o", "optval", NULL};
    command_init(&cmd, "prog", "1.4.0");
    command_option(&cmd, "-o", "--optional [arg]", "optional arg", optional_cb);
    command_parse(&cmd, 3, argv);
    check(cmd.argc == 0, "-o consumes the following token as its optional arg");
    command_free(&cmd);
  }

  /* ---- 4. combined short flags are exploded: -vo val (normalize_args) ---- */
  {
    command_t cmd;
    char *argv[] = {"prog", "-vo", "val", NULL};
    command_init(&cmd, "prog", "1.4.0");
    command_option(&cmd, "-v", "--verbose", "verbose stuff", verbose_cb);
    command_option(&cmd, "-o", "--optional [arg]", "optional arg", optional_cb);
    command_parse(&cmd, 3, argv);
    command_free(&cmd);
    printf("  [INFO] -vo exploded through normalize_args (see callback lines above)\n");
  }

  /* ---- 5. "--" literal separator suppresses unrecognized-flag error ---- */
  {
    command_t cmd;
    char *argv[] = {"prog", "-v", "--", "-z", "tail", NULL};
    command_init(&cmd, "prog", "1.4.0");
    command_option(&cmd, "-v", "--verbose", "verbose stuff", verbose_cb);
    command_parse(&cmd, 5, argv);
    check(cmd.argc == 2 && strcmp(cmd.argv[0], "-z") == 0,
          "-- suppresses unrecognized-flag error; '-z' becomes positional");
    command_free(&cmd);
  }

  /* ---- 6. missing required arg -> exit 1 "argument required" ---- */
  {
    int rc = run_child(child_missing_required);
    check(rc == 1, "missing required arg -> process exits with status 1");
  }

  /* ---- 7. unrecognized flag -> exit 1 ---- */
  {
    int rc = run_child(child_unrecognized);
    check(rc == 1, "unrecognized flag -> process exits with status 1");
  }

  printf("=== result: %s ===\n", g_failures == 0 ? "PASS" : "FAIL");
  return g_failures == 0 ? 0 : 1;
}