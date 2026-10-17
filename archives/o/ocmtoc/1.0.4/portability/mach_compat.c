/* POSIX implementation of the Mach VM/host helpers declared in
 * portability/shim/mach/mach.h, for the libstuff sources linked into
 * mtoc on non-Apple platforms (e.g. HarmonyOS).
 *
 *   - vm_allocate(): calloc() gives the same observable behavior as
 *     vm_allocate() here (anonymous, zero-filled); writeout.c even relies
 *     on holes reading as zero bytes.
 *   - vm_deallocate(): ofile images are created with mmap(), so munmap()
 *     is the correct release; free() is kept as a fallback for buffers
 *     that came from the allocator.
 *   - host_info(HOST_BASIC_INFO): backed by uname(), mapped to the
 *     CPU_TYPE_* constants from <mach/machine-cctools.h>. Only used by
 *     get_arch_from_host(), which mtoc reaches solely for `-arch host`
 *     style queries; returning the real host CPU is the truthful answer.
 *   - ocmtoc_reallocf(): BSD reallocf(3) semantics (free on failure),
 *     exposed to all TUs as `reallocf` via the forced-include
 *     portability/shim/ocmtoc_compat.h; used by libstuff/diagnostics.c.
 */
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/utsname.h>

#include <mach/mach.h>
#include <mach/machine.h>

kern_return_t
vm_allocate(vm_task_t target, vm_address_t *address, vm_size_t size,
            int anywhere)
{
    (void)target;
    (void)anywhere;
    void *p;

    if (size == 0) {
        *address = (vm_address_t)0;
        return KERN_SUCCESS;
    }
    p = calloc(1, (size_t)size);
    if (p == NULL)
        return -1;
    *address = (vm_address_t)(uintptr_t)p;
    return KERN_SUCCESS;
}

kern_return_t
vm_deallocate(vm_task_t target, vm_address_t address, vm_size_t size)
{
    (void)target;

    if (address == (vm_address_t)0)
        return KERN_SUCCESS;
    if (munmap((void *)(uintptr_t)address, (size_t)size) == 0)
        return KERN_SUCCESS;
    /* Not an mmap'd region (e.g. calloc'd buffer): release via free(). */
    free((void *)(uintptr_t)address);
    return KERN_SUCCESS;
}

kern_return_t
host_info(mach_port_t host, int flavor, host_info_t info,
          unsigned int *count)
{
    struct utsname u;
    struct host_basic_info *hbi = (struct host_basic_info *)info;
    int cputype = 0;
    int cpusubtype = 0;

    (void)host;
    if (flavor != HOST_BASIC_INFO || info == NULL)
        return -1;
    memset(hbi, 0, sizeof(*hbi));
    if (uname(&u) != 0)
        return -1;
#if defined(__aarch64__) || defined(__arm64__)
    cputype = CPU_TYPE_ARM64;
    cpusubtype = CPU_SUBTYPE_ARM64_ALL;
#elif defined(__x86_64__) || defined(__x86_64)
    cputype = CPU_TYPE_X86_64;
    cpusubtype = CPU_SUBTYPE_X86_64_ALL;
#elif defined(__i386__) || defined(__i386)
    cputype = CPU_TYPE_I386;
    cpusubtype = CPU_SUBTYPE_I386_ALL;
#elif defined(__arm__)
    cputype = CPU_TYPE_ARM;
    cpusubtype = CPU_SUBTYPE_ARM_ALL;
#endif
    hbi->cpu_type = cputype;
    hbi->cpu_subtype = cpusubtype;
    if (count != NULL)
        *count = HOST_BASIC_INFO_COUNT;
    return KERN_SUCCESS;
}

/* BSD reallocf(3) for non-Apple platforms (see ocmtoc_compat.h).
 *
 * Same observable semantics as the macOS function: identical to realloc()
 * on success; on failure the input pointer is freed and NULL is returned.
 * Used by libstuff/diagnostics.c (diagnostic message list growth).
 */
void *
ocmtoc_reallocf(void *ptr, size_t size)
{
    void *p;

    p = realloc(ptr, size);
    if (p == NULL && size != 0)
        free(ptr);
    return p;
}
