/* Portability shim: <machine/types.h> for non-Apple platforms.
 *
 * Upstream include/stuff/bytesex.h includes <machine/types.h> to get the
 * basic integer types used by the <mach/<arch>/thread_status.h> headers.
 * That path is a system SDK header on macOS; the ocmtoc repo ships no
 * include/machine/ directory (verified via the 1.0.4 tree: include/ has
 * architecture/coff/elf/gnu/i386/llvm-c/mach-o/mach/modules/opcode/
 * standalone/stuff/sys/xar, but no machine/). On HarmonyOS/musl the same
 * types live in the standard headers aggregated below.
 */
#ifndef OCMTOC_PORT_MACHINE_TYPES_H
#define OCMTOC_PORT_MACHINE_TYPES_H

#include <sys/types.h>
#include <stdint.h>

/* Upstream <mach/i386/_structs.h> (via <mach/i386/thread_status.h>) does
 * `#include <machine/types.h>  // __uint8_t` and then uses the Darwin
 * double-underscore integer types throughout the x86 thread/float states.
 * musl/glibc provide uint8_t etc. but not the __uint32_t spelling, so
 * alias them here. Guarded so an SDK that already defines them wins.
 * No platform macros; Linux/OHOS generic.
 */
#ifndef __uint8_t
typedef uint8_t __uint8_t;
#endif
#ifndef __uint16_t
typedef uint16_t __uint16_t;
#endif
#ifndef __uint32_t
typedef uint32_t __uint32_t;
#endif
#ifndef __uint64_t
typedef uint64_t __uint64_t;
#endif
#ifndef __int8_t
typedef int8_t __int8_t;
#endif
#ifndef __int16_t
typedef int16_t __int16_t;
#endif
#ifndef __int32_t
typedef int32_t __int32_t;
#endif
#ifndef __int64_t
typedef int64_t __int64_t;
#endif

#endif /* OCMTOC_PORT_MACHINE_TYPES_H */
