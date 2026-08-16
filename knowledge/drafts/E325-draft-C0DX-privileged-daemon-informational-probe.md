# E325 - Allowlist informational daemon probes before mandatory configuration

## Error surface

An installed system daemon cannot answer a pure information request in a clean
consumer environment:

```text
tool --version
Can't open options file /system/or/etc/path: No such file or directory
exit != 0
```

The same binary may compile, link and package correctly. The failure appears
only before deployment because the host-wide configuration tree has not been
created yet.

## Trigger conditions

Use this pattern only when all conditions hold:

1. The affected options are strictly informational, such as an upstream
   `--version` or `--help` handler.
2. Those handlers do not require configuration, credentials, devices, sockets,
   network changes or service initialization.
3. The program currently loads mandatory global configuration before parsing
   the command line.
4. The existing upstream argument parser can preserve the canonical output and
   exit status.
5. Every non-informational or mixed argument list can remain on the original
   configuration and initialization path.

Do not use this pattern to make operational subcommands work without policy or
configuration.

## Root cause

Traditional system daemons often assume they run only after host deployment.
Their startup order may therefore be:

1. initialize a platform channel;
2. read a mandatory system options file;
3. read user configuration; and
4. parse command-line arguments.

Packaging and consumer tests intentionally run before global deployment. A
version/help request reaches step 2 first and fails even though it would have
exited without using the loaded state. Creating fake host configuration hides
the ordering defect and makes the test mutate global state.

## Recommended contract

Add a narrow, fail-closed dispatch before mandatory configuration:

1. Require exactly one user argument (`argc == 2`).
2. Match a fixed allowlist of upstream informational spellings.
3. Call the existing upstream parser or handler; do not duplicate output.
4. Let that handler retain its upstream exit code.
5. Leave all other argument counts and values on the original startup path.
6. Guard a platform-specific reorder with the platform's precise macro when
   the upstream order must remain unchanged elsewhere.

A representative shape is:

```c
#ifdef __OHOS__
if (argc == 2 && is_exact_informational_option(argv[1]))
    parse_args(argc - 1, argv + 1);
#endif
```

This is safe only when the selected upstream handlers terminate immediately.
If the parser merely sets state and returns, use a dedicated upstream handler
or the staged-config fallback instead.

## Consumer verification matrix

A positive-only `--version` smoke test is insufficient. Verify three distinct
contracts against the installed binary:

| Check | Expected result | Purpose |
|---|---|---|
| exact version option | exit 0 and canonical version | proves a real information handler runs |
| exact help option | exit 0 and upstream usage marker | covers a separate information surface |
| explicit missing config option | nonzero | proves operational parsing did not gain the bypass |

Use a unique nonexistent path under the test `TMPDIR`; do not create or delete
host configuration. Keep network, device and privileged operations out of this
test.

## Forbidden approaches

- Do not scan the entire argv for `--version`; mixed arguments could bypass
  required initialization.
- Do not process arbitrary options before mandatory configuration.
- Do not print a hard-coded version from a wrapper or test fixture.
- Do not create `/etc`, `/system` or service configuration solely for smoke
  testing.
- Do not report an information probe as proof that privileged service behavior
  works.

## Difference from existing knowledge

- E214 concerns a shell `read` that blocks a non-interactive process. E325 is a
  native daemon control-flow ordering problem with no interactive input.
- E246 concerns SIGSYS/seccomp after a restricted syscall. E325 prevents a pure
  handler from being blocked before any operational syscall should be needed.
- E091 and E163 concern OHOS/Linux header compile or link failures. E325 applies
  after the binary has already built and packaged successfully.

## ppp example and candidate validation

In ppp 2.5.2, `pppd/main.c` loads the mandatory system options file before
`parse_args()`. An unprivileged clean-package invocation therefore cannot reach
the upstream `showversion()` or `showhelp()` handlers. The OHOS patch accepts
only one of `--version`, `-v`, `--help`, or `-h`, then calls the upstream parser.

The candidate package consumer is designed to check the exact 2.5.2 version,
the upstream help marker, and rejection of an explicitly missing options file.
The updated assertions await the current-head official CI run. The test does not
open `/dev/ppp`, create a session, alter routes or claim live PPP/PPPoE support.

## Related entries

- E214: interactive shell reads in non-interactive testing.
- E246: restricted Linux syscalls and safe feature-subset probes.
- E091: `sockaddr_storage` conflict in OHOS Linux compatibility headers.
- E163: `__packed` duplicate symbol from compatibility headers.
