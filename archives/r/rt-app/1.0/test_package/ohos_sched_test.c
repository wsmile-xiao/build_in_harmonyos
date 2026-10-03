/*
 * HarmonyOS-specific verification for the rt-app package.
 *
 * Two things are checked, both against the artifact and platform that the
 * adaptation actually targets:
 *
 *  1. The delivered `rt-app` executable is a genuine 64-bit AArch64 ELF.
 *     The ELF header is parsed directly with plain C (no external tooling),
 *     so this works on the minimal OHOS worker image.
 *
 *  2. The scheduling surface that the OHOS adaptation rewired still works.
 *     rt-app pins its worker threads to CPUs and yields the remainder of a
 *     period; upstream used the glibc-only GNU extensions
 *     pthread_getaffinity_np() / pthread_setaffinity_np() / pthread_yield(),
 *     which musl-based libc (the OHOS C library) does not provide. The recipe
 *     replaces them with POSIX sched_getaffinity() / sched_setaffinity() /
 *     sched_yield(), and rt-app stores its masks in cpu_set_t.
 *
 *     This file only compiles and runs if that surface really exists, so it
 *     fails loudly if a future patch regresses the adaptation.
 */
#define _GNU_SOURCE

#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if !defined(__aarch64__)
#error "the rt-app HarmonyOS test must be compiled for aarch64"
#endif

#define EI_NIDENT   16
#define ELFCLASS64  2
#define EM_AARCH64  183

static int assertions;
static int failures;

static void check(int ok, const char *what)
{
    assertions++;
    if (ok) {
        printf("ok - %s\n", what);
    } else {
        printf("not ok - %s\n", what);
        failures++;
    }
}

/* Verify that `path` is a 64-bit AArch64 ELF executable. */
static void verify_elf(const char *path)
{
    unsigned char ident[EI_NIDENT];
    uint16_t machine;
    FILE *f = fopen(path, "rb");
    if (!f) {
        check(0, "the packaged rt-app executable can be opened");
        return;
    }
    check(1, "the packaged rt-app executable can be opened");

    if (fread(ident, 1, sizeof(ident), f) != sizeof(ident)) {
        fclose(f);
        check(0, "the packaged rt-app executable has a readable ELF header");
        return;
    }
    fclose(f);

    check(ident[0] == 0x7f && ident[1] == 'E' && ident[2] == 'L' && ident[3] == 'F',
          "the packaged rt-app executable carries the ELF magic");
    check(ident[4] == ELFCLASS64, "the packaged rt-app executable is 64-bit");
    /* e_machine lives at offset 18 in a little-endian ELF64 header. */
    f = fopen(path, "rb");
    if (f) {
        unsigned char buf[2] = {0, 0};
        if (fseek(f, 18, SEEK_SET) == 0 && fread(buf, 1, 2, f) == 2)
            machine = (uint16_t)(buf[0] | (buf[1] << 8));
        else
            machine = 0;
        fclose(f);
    } else {
        machine = 0;
    }
    check(machine == EM_AARCH64, "the packaged rt-app executable targets AArch64");
}

int main(int argc, char **argv)
{
    cpu_set_t current, requested, saved;
    cpu_set_t *cpu_alloc_set, *heap_set;
    size_t alloc_size, copy_size;
    int cpu_count, ret;

    printf("--- rt-app HarmonyOS verification ---\n");

    verify_elf(argc > 1 ? argv[1] : "rt-app");

    printf("--- sched/cpu_set_t adaptation surface ---\n");

    memset(&current, 0, sizeof(current));
    memset(&saved, 0, sizeof(saved));

    /* sched_getaffinity(0, ...) is the POSIX spelling of
     * pthread_getaffinity_np(pthread_self(), ...). */
    ret = sched_getaffinity(0, sizeof(current), &current);
    check(ret == 0, "sched_getaffinity(0) returns the calling thread affinity");

    cpu_count = CPU_COUNT(&current);
    check(cpu_count > 0, "the affinity mask reports at least one CPU");

    /* The heap-allocated cpuset_data_t path used by rt-app set_thread_affinity().
     *
     * CPU_ALLOC_SIZE(n) is NOT sizeof(cpu_set_t). On OHOS/musl it is
     *   sizeof(long) * ceil(n / (8*sizeof(long)))
     * i.e. 8 bytes on aarch64 for any device with up to 64 CPUs, whereas
     * CPU_EQUAL() is CPU_EQUAL_S(sizeof(cpu_set_t), ...), a 128-byte memcmp.
     * Copying only CPU_ALLOC_SIZE() bytes into a CPU_ALLOC() buffer and then
     * calling CPU_EQUAL() therefore reads 120 bytes past the end of that
     * allocation and compares recycled heap. That is unsound, and it only
     * appeared to pass where the allocator happened to hand back zeroed pages.
     *
     * So exercise CPU_ALLOC() on its advertised size, and separately compare a
     * full mask through a buffer that really covers what CPU_EQUAL reads.
     */
    /* Make the heap check meaningful first: on a running device CPU_ALLOC hands
     * back recycled memory, so fill and release a few same-sized chunks. Without
     * this the comparison below would pass on freshly zeroed pages alone, which
     * is exactly what hid the overread. */
    for (int i = 0; i < 64; i++) {
        void *dirty = calloc(1, sizeof(cpu_set_t));
        if (dirty) {
            memset(dirty, 0xA5, sizeof(cpu_set_t));
            free(dirty);
        }
    }

    alloc_size = CPU_ALLOC_SIZE(cpu_count);
    cpu_alloc_set = CPU_ALLOC(cpu_count);
    check(cpu_alloc_set != NULL && alloc_size >= sizeof(long),
          "CPU_ALLOC returns a heap cpuset of at least one machine word");
    if (cpu_alloc_set) {
        copy_size = alloc_size < sizeof(cpu_set_t) ? alloc_size : sizeof(cpu_set_t);
        memcpy(cpu_alloc_set, &current, copy_size);
        check(CPU_EQUAL_S(alloc_size, cpu_alloc_set, &current),
              "the CPU_ALLOC buffer carries the mask across all advertised CPUs");
        CPU_FREE(cpu_alloc_set);
    }

    heap_set = (cpu_set_t *)calloc(1, sizeof(cpu_set_t));
    check(heap_set != NULL, "a full-size heap cpu_set_t can be allocated");
    if (heap_set) {
        memcpy(heap_set, &current, sizeof(cpu_set_t));
        check(CPU_EQUAL(heap_set, &current),
              "a heap-allocated cpu_set_t compares equal to the mask");
        free(heap_set);
    }

    check(sched_getaffinity(0, sizeof(saved), &saved) == 0,
          "the original affinity mask can be saved");

    /* Pin to CPU 0 and restore, exactly as rt-app main() wraps calibration in. */
    CPU_ZERO(&requested);
    CPU_SET(0, &requested);
    ret = sched_setaffinity(0, sizeof(requested), &requested);
    check(ret == 0, "sched_setaffinity(0) pins the thread to CPU 0");

    memset(&current, 0, sizeof(current));
    ret = sched_getaffinity(0, sizeof(current), &current);
    check(ret == 0 && CPU_COUNT(&current) == 1 && CPU_ISSET(0, &current),
          "the thread now reports exactly CPU 0 as its affinity");

    ret = sched_setaffinity(0, sizeof(saved), &saved);
    check(ret == 0, "the original affinity mask is restored");

    /* rt-app's rtapp_yield event calls sched_yield() now. */
    sched_yield();
    check(1, "sched_yield() is available and returns");

    printf("HarmonyOS assertions: %d run, %d passed, %d failed\n",
           assertions, assertions - failures, failures);
    return failures ? 1 : 0;
}
