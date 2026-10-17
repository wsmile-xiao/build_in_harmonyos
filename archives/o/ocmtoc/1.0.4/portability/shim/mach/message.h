/* Portability shim: <mach/message.h> for non-Apple platforms (e.g. HarmonyOS).
 *
 * Upstream cctools thread_status headers (<mach/<arch>/thread_status.h>)
 * unconditionally `#include <mach/message.h>` (system SDK header on macOS)
 * and use `mach_msg_type_number_t` for the *_STATE_COUNT macros
 * (e.g. include/mach/ppc/thread_status.h:36). That SDK header does not
 * exist on HarmonyOS/musl, so compilation stops at:
 *   fatal error: 'mach/message.h' file not found
 * via include/stuff/bytesex.h -> include/mach/ppc/thread_status.h.
 *
 * Only the type used by those headers is provided here. mtoc never sends
 * Mach IPC messages, so no message structs or trap declarations are needed.
 * No platform macro is used; this is a pure missing-system-header shim.
 */
#ifndef OCMTOC_PORT_MACH_MESSAGE_H
#define OCMTOC_PORT_MACH_MESSAGE_H

typedef unsigned int mach_msg_type_number_t;

#endif /* OCMTOC_PORT_MACH_MESSAGE_H */
