/* Portability shim: <mach/mach.h> for non-Apple platforms (e.g. HarmonyOS).
 *
 * Only the small subset of the Mach API actually used by the libstuff
 * sources linked into mtoc is provided. Semantics are POSIX equivalents:
 *   - anonymous zero-filled memory: vm_allocate -> calloc, vm_deallocate ->
 *     munmap (for mmap'd file images) with free() fallback;
 *   - host identity: mach_task_self()/mach_host_self() are dummy ports,
 *     mach_port_deallocate() is a no-op, host_info() is backed by uname()
 *     (see mach_compat.c);
 *   - mach_error_string() returns a static message (only used on paths
 *     that also print the program's own diagnostics).
 */
#ifndef OCMTOC_PORT_MACH_MACH_H
#define OCMTOC_PORT_MACH_MACH_H

#include <stdint.h>
#include <stddef.h>

#ifndef __private_extern__
#define __private_extern__ extern
#endif

typedef int kern_return_t;
#define KERN_SUCCESS 0

typedef unsigned int mach_port_t;
#define MACH_PORT_NULL 0
#define mach_task_self() ((mach_port_t)0)
#define mach_host_self() ((mach_port_t)0)

static inline kern_return_t
mach_port_deallocate(mach_port_t task, mach_port_t name)
{
    (void)task;
    (void)name;
    return KERN_SUCCESS;
}

static inline const char *
mach_error_string(kern_return_t r)
{
    (void)r;
    return "Mach call failed (no Mach on this platform)";
}

/* Virtual memory (anonymous, zero-filled). */
typedef uintptr_t vm_address_t;
typedef uint64_t vm_size_t;
typedef mach_port_t vm_task_t;

kern_return_t vm_allocate(vm_task_t target, vm_address_t *address,
                          vm_size_t size, int anywhere);
kern_return_t vm_deallocate(vm_task_t target, vm_address_t address,
                            vm_size_t size);

/* Host info (uname-backed, see mach_compat.c). */
typedef int *host_info_t;
struct host_basic_info {
    int cpu_type;
    int cpu_subtype;
    int reserved_[8];
};
#define HOST_BASIC_INFO 1
#define HOST_BASIC_INFO_COUNT \
    ((int)(sizeof(struct host_basic_info) / sizeof(int)))

kern_return_t host_info(mach_port_t host, int flavor, host_info_t info,
                        unsigned int *count);

#endif /* OCMTOC_PORT_MACH_MACH_H */
