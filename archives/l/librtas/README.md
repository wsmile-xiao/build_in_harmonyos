# librtas

User-space library for Run-Time Abstraction Services (RTAS) calls, adapted for OpenHarmony.

- Upstream: https://github.com/ibm-power-utilities/librtas
- Version: 2.0.4
- Current package: `archives/l/librtas/2.0.4`
- Supported OpenHarmony architecture: armv8
- License: LGPL-2.1-or-later

The recipe delivers both upstream libraries without modification:

- `librtas.so` — wrappers around the ppc64 RTAS system call. HarmonyOS aarch64
  has no such kernel interface, so these entry points return librtas' own
  documented error codes at runtime. See `2.0.4/notes.md` for the full evidence.
- `librtasevent.so` — the architecture-neutral RTAS error-log event parser and
  printer. Fully functional; covered by the package tests.
