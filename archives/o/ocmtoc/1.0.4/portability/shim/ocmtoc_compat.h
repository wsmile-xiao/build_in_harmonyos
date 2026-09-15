/* Forced-include compatibility header for non-Apple platforms.
 *
 * The recipe compiles every translation unit with
 *   -include <portability/shim>/ocmtoc_compat.h
 * so the declarations below are visible in all upstream sources without
 * patching them and without shadowing any system header.
 *
 * reallocf(3) exists only on BSD/macOS: like realloc(), but frees the
 * input pointer when reallocation fails. musl/HarmonyOS provides no such
 * function, so libstuff/diagnostics.c fails with:
 *   error: incompatible integer to pointer conversion assigning to
 *   'struct diagnostic *' from 'int' (implicit declaration).
 * Call sites keep spelling `reallocf`; the macro redirects them to the
 * implementation in portability/mach_compat.c with identical semantics.
 * No platform macros; Linux/OHOS generic.
 */
#ifndef OCMTOC_PORT_COMPAT_H
#define OCMTOC_PORT_COMPAT_H

#include <stddef.h>

void *ocmtoc_reallocf(void *ptr, size_t size);

#define reallocf ocmtoc_reallocf

#endif /* OCMTOC_PORT_COMPAT_H */
