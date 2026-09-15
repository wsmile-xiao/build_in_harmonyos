/* Portability shim: <mach/boolean.h> for non-Apple platforms.
 *
 * Upstream include/mach/machine-cctools.h does
 * `#import <mach/boolean.h>`, which on macOS resolves to the SDK header
 * (itself a wrapper over mach/machine/boolean.h + TRUE/FALSE). The ocmtoc
 * repo ships no mach/boolean.h, so provide the minimal definition used by
 * machine-cctools.h (boolean_t + TRUE/FALSE). Matches the ARM SDK where
 * boolean_t is int. No platform macros; Linux/OHOS generic.
 */
#ifndef OCMTOC_PORT_MACH_BOOLEAN_H
#define OCMTOC_PORT_MACH_BOOLEAN_H

typedef int boolean_t;

#ifndef TRUE
#define TRUE 1
#endif

#ifndef FALSE
#define FALSE 0
#endif

#endif /* OCMTOC_PORT_MACH_BOOLEAN_H */
