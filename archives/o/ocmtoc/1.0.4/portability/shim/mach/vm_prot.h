/* Portability shim: <mach/vm_prot.h> for non-Apple platforms.
 *
 * Upstream include/mach-o/loader.h conditionally pulls this header:
 *   #if __has_include(<mach/vm_prot.h>)
 *   #include <mach/vm_prot.h>
 *   #endif
 * On macOS it resolves to the SDK header providing vm_prot_t and the
 * VM_PROT_* constants; the ocmtoc repo ships no such file, so on
 * HarmonyOS the include is silently skipped and efitools/mtoc.c fails
 * with:
 *   error: use of undeclared identifier 'VM_PROT_READ' / 'VM_PROT_WRITE'
 * (segment initprot checks in process_32bit_arch/process_64bit_arch and
 * the first-writable-segment detection in create_base_reloc).
 *
 * Values below match the Darwin SDK (osfmk/mach/vm_prot.h). Because the
 * -Iportability/shim path is searched first, upstream loader.h picks
 * this shim up automatically via its own __has_include gate, so every
 * translation unit that includes <mach-o/loader.h> gets the constants
 * with no source patch. No platform macros; Linux/OHOS generic.
 */
#ifndef OCMTOC_PORT_MACH_VM_PROT_H
#define OCMTOC_PORT_MACH_VM_PROT_H

typedef int vm_prot_t;

#define VM_PROT_NONE ((vm_prot_t)0x00)
#define VM_PROT_READ ((vm_prot_t)0x01)
#define VM_PROT_WRITE ((vm_prot_t)0x02)
#define VM_PROT_EXECUTE ((vm_prot_t)0x04)
#define VM_PROT_NO_CHANGE ((vm_prot_t)0x08)
#define VM_PROT_COPY ((vm_prot_t)0x10)
#define VM_PROT_WANTS_COPY ((vm_prot_t)0x20)
#define VM_PROT_IS_MASK ((vm_prot_t)0x40)

#define VM_PROT_ALL (VM_PROT_READ | VM_PROT_WRITE | VM_PROT_EXECUTE)
#define VM_PROT_DEFAULT VM_PROT_ALL
#define VM_PROT_INITIAL VM_PROT_DEFAULT

#endif /* OCMTOC_PORT_MACH_VM_PROT_H */
