/* Portability shim: <mach/machine.h> for non-Apple platforms.
 *
 * Apple's <mach/machine.h> is a wrapper that pulls in the CPU type
 * definitions. This repo already ships them as
 * <mach/machine-cctools.h>, so just forward to it.
 */
#ifndef OCMTOC_PORT_MACH_MACHINE_H
#define OCMTOC_PORT_MACH_MACHINE_H

#include <mach/machine-cctools.h>

#endif /* OCMTOC_PORT_MACH_MACHINE_H */
