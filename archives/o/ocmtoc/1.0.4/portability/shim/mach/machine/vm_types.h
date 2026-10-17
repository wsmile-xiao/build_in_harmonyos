/* Portability shim: <mach/machine/vm_types.h> for non-Apple platforms.
 *
 * Upstream include/mach/machine-cctools.h does
 * `#import <mach/machine/vm_types.h>`, which on macOS resolves to the SDK
 * header (mach/arm/vm_types.h etc.). The ocmtoc repo ships no such file,
 * so provide the minimal LP64 definitions machine-cctools.h actually uses
 * (vm_size_t in struct machine_info, integer_t for cpu_threadtype_t).
 * Spelling matches the SDK LP64 branch (uintptr_t/vm_size_t as 64-bit,
 * integer_t as int) and portability/shim/mach/mach.h, so the benign
 * duplicate typedef of vm_size_t across both headers stays identical.
 * No platform macros; Linux/OHOS generic.
 */
#ifndef OCMTOC_PORT_MACH_MACHINE_VM_TYPES_H
#define OCMTOC_PORT_MACH_MACHINE_VM_TYPES_H

#include <stdint.h>

typedef uintptr_t vm_offset_t;
typedef uint64_t vm_size_t;

typedef int integer_t;
typedef unsigned int natural_t;

typedef uint64_t mach_vm_address_t;
typedef uint64_t mach_vm_offset_t;
typedef uint64_t mach_vm_size_t;

typedef uint64_t vm_map_offset_t;
typedef uint64_t vm_map_address_t;
typedef uint64_t vm_map_size_t;

#endif /* OCMTOC_PORT_MACH_MACHINE_VM_TYPES_H */
