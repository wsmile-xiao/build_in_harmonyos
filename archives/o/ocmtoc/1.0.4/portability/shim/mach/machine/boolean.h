/* Portability shim: <mach/machine/boolean.h> for non-Apple platforms.
 *
 * Upstream include/mach/hppa/thread_status.h does
 * `#include <mach/machine/boolean.h>` for boolean_t (used by the
 * hp_pa_frame_thread_state alignment/execution trap-reflect flags). On
 * macOS that resolves to the SDK header; the ocmtoc repo ships no
 * mach/machine/boolean.h, so compilation stops at:
 *   fatal error: 'mach/machine/boolean.h' file not found
 * via include/stuff/bytesex.h -> include/mach/hppa/thread_status.h
 * (reached from include/stuff/ofile.h, as seen in the preflight log).
 *
 * The single source of truth for boolean_t stays in <mach/boolean.h>;
 * this wrapper includes it so that including either or both headers
 * yields exactly one definition (no duplicate-typedef risk on strict
 * compilers). Matches the SDK where boolean_t is int. No platform
 * macros; Linux/OHOS generic.
 */
#ifndef OCMTOC_PORT_MACH_MACHINE_BOOLEAN_H
#define OCMTOC_PORT_MACH_MACHINE_BOOLEAN_H

#include <mach/boolean.h>

#endif /* OCMTOC_PORT_MACH_MACHINE_BOOLEAN_H */
