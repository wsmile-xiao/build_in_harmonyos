# pathload 1.3.2 adaptation notes

The immutable upstream release uses an old autoconf 2.13 generated configure
script and a custom lower-case makefile. The recipe keeps that build system and
packages the two upstream command-line programs: `pathload_snd` and
`pathload_rcv`.

The recipe applies small, deterministic source replacements for issues already
carried by downstream ports: the old implicit-int configure probe, modern C
compiler signal-handler prototypes, the receiver `main()` parameter type, and
the makefile link order. It also stops the default `all` target from deleting
object files during the build, matching current distribution maintenance
practice.

The upstream tarball does not provide a check/test target. The added consumer
test verifies both packaged executables exist, checks sender and receiver help
output, confirms the receiver documents the required sender argument, and
exercises a missing-sender invocation without starting network bandwidth
measurement.

COMPLETED
