/* test_package.c — libdwarfp/2.1.0 conan test_package.

R34: this test must actually call the tested package's API.
libdwarfp is the DWARF producer (write) library of the libdwarf
project:
- Library verification: find_package(libdwarfp) + target_link_libraries
- API verification    : dwarf_producer_init() -> dwarf_new_die_a()
  -> dwarf_add_AT_name_a() -> dwarf_add_die_to_debug_a()
  -> dwarf_transform_to_disk_form_a() -> dwarf_get_section_bytes_a()
  -> dwarf_producer_finish_a(), plus the unknown-ISA error path.
  Static linking pulls the libdwarf consumer library in through the
  libdwarfp producer API symbols (dwarf_encode_leb128 & co.).

The run produces a real (in-memory) .debug_info/.debug_abbrev section
pair for an arm64 DWARF5 target and validates the CU header.
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <dwarf.h>
#include <libdwarf.h>
#include <libdwarfp.h>

static int g_failures = 0;

#define ASSERT(cond, msg)                                                  \
    do {                                                                   \
        if (!(cond)) {                                                     \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);        \
            ++g_failures;                                                  \
        } else {                                                           \
            printf("ok: %s\n", msg);                                       \
        }                                                                  \
    } while (0)

/*  Section callback: the producer invokes it once per DWARF section
    it is about to emit ("name" e.g. ".debug_info").  Like upstream
    dwarfgen we hand back a per-section index and record the names so
    the test can locate the .debug_info buffer below. */
typedef struct {
    char name[64];
    Dwarf_Unsigned index;
} recorded_section_t;

static recorded_section_t g_sections[8];
static unsigned g_nsections;

static int
section_callback(const char *name,
    int size,
    Dwarf_Unsigned type,
    Dwarf_Unsigned flags,
    Dwarf_Unsigned link,
    Dwarf_Unsigned info,
    Dwarf_Unsigned *sect_name_index,
    void *user_data,
    int *errcode)
{
    unsigned next_index = g_nsections;

    (void)size;
    (void)type;
    (void)flags;
    (void)link;
    (void)info;
    (void)user_data;
    (void)errcode;
    if (!strncmp(name, ".rel", 4)) {
        /*  Symbolic relocations: no relocation section emitted
            (same approach as upstream dwarfgen). */
        return 0;
    }
    if (next_index < (sizeof(g_sections) / sizeof(g_sections[0]))) {
        strncpy(g_sections[next_index].name, name,
            sizeof(g_sections[next_index].name) - 1);
        g_sections[next_index].name[sizeof(g_sections[next_index].name) - 1] = 0;
        g_sections[next_index].index = (Dwarf_Unsigned)next_index;
    }
    ++g_nsections;
    /*  Any nonzero per-section symbol index; the producer just
        stores it for relocation records. */
    *sect_name_index = (Dwarf_Unsigned)next_index + 1;
    return (int)next_index;
}

static const char *
find_section_name(Dwarf_Unsigned index)
{
    unsigned i;
    unsigned limit = (sizeof(g_sections) / sizeof(g_sections[0]));

    for (i = 0; i < g_nsections && i < limit; ++i) {
        if (g_sections[i].index == index) {
            return g_sections[i].name;
        }
    }
    return NULL;
}

static char g_cu_name[] = "test_package.c";

int
main(void)
{
    Dwarf_P_Debug dbg = NULL;
    Dwarf_P_Die cudie = NULL;
    Dwarf_P_Attribute attr = NULL;
    Dwarf_Error err = NULL;
    Dwarf_Unsigned nbufs = 0;
    int have_info = 0;
    int have_abbrev = 0;
    int info_version_ok = 0;
    int res;

    /*  Unbuffered so progress is visible even if a later step
        aborts. */
    setvbuf(stdout, NULL, _IONBF, 0);

    /*  1. Producer init: arm64 / DWARF5 / 64-bit pointers /
          little endian / symbolic relocations. */
    res = dwarf_producer_init(
        DW_DLC_POINTER64 | DW_DLC_TARGET_LITTLEENDIAN |
            DW_DLC_SYMBOLIC_RELOCATIONS,
        section_callback,
        NULL,   /* errhand */
        NULL,   /* errarg */
        NULL,   /* user_data */
        "arm64",
        "V5",
        "",     /* extra */
        &dbg,
        &err);
    ASSERT(res == DW_DLV_OK && dbg != NULL,
        "dwarf_producer_init(arm64,V5) returns DW_DLV_OK");

    /*  2. Compile-unit DIE with a name attribute. */
    if (res == DW_DLV_OK) {
        res = dwarf_new_die_a(dbg, DW_TAG_compile_unit,
            NULL, NULL, NULL, NULL, &cudie, &err);
        ASSERT(res == DW_DLV_OK && cudie != NULL,
            "dwarf_new_die_a(DW_TAG_compile_unit) returns DW_DLV_OK");
    }
    if (res == DW_DLV_OK && cudie) {
        res = dwarf_add_AT_name_a(cudie, g_cu_name, &attr, &err);
        ASSERT(res == DW_DLV_OK && attr != NULL,
            "dwarf_add_AT_name_a() returns DW_DLV_OK");
    }
    if (res == DW_DLV_OK && cudie) {
        res = dwarf_add_die_to_debug_a(dbg, cudie, &err);
        ASSERT(res == DW_DLV_OK,
            "dwarf_add_die_to_debug_a() returns DW_DLV_OK");
    }

    /*  3. Transform the DIE tree into in-memory section buffers. */
    if (res == DW_DLV_OK) {
        res = dwarf_transform_to_disk_form_a(dbg, &nbufs, &err);
        ASSERT(res == DW_DLV_OK && nbufs > 0,
            "dwarf_transform_to_disk_form_a() emits section buffers");
    }
    ASSERT(g_nsections >= 2,
        "producer registered >= 2 sections (.debug_info/.debug_abbrev)");

    /*  4. Walk the emitted buffers and locate .debug_info through
        the section index our callback assigned. */
    for (;;) {
        Dwarf_Unsigned sect_idx = 0;
        Dwarf_Unsigned length = 0;
        Dwarf_Ptr bytes = NULL;
        const unsigned char *ub = NULL;
        const char *sname = NULL;

        res = dwarf_get_section_bytes_a(dbg, 0, &sect_idx, &length,
            &bytes, &err);
        if (res != DW_DLV_OK) {
            break;
        }
        sname = find_section_name(sect_idx);
        if (sname && !strcmp(sname, ".debug_info")) {
            have_info = 1;
            /*  DWARF5 CU header: unit_length(4 bytes) then
                version (2 bytes, little endian) == 5. */
            ub = (const unsigned char *)bytes;
            if (length > 8 && ub != NULL &&
                ub[4] == 5 && ub[5] == 0 && ub[0] != 0) {
                info_version_ok = 1;
            }
        } else if (sname && !strcmp(sname, ".debug_abbrev")) {
            have_abbrev = (length > 0 && bytes != NULL);
        }
    }
    ASSERT(have_info, ".debug_info section buffer present");
    ASSERT(have_abbrev, ".debug_abbrev section buffer present");
    ASSERT(info_version_ok,
        ".debug_info begins with a DWARF5 CU header");

    /*  5. Tear the producer down. */
    if (dbg) {
        res = dwarf_producer_finish_a(dbg, &err);
        ASSERT(res == DW_DLV_OK,
            "dwarf_producer_finish_a() returns DW_DLV_OK");
        dbg = NULL;
    }

    /*  6. Error path: an unknown ISA name must fail.  NOTE: a
        producer error uses the producer-private Dwarf_Error layout,
        so it must NOT be passed to consumer calls like
        dwarf_errmsg() (undefined behavior); only the failure is
        asserted here. */
    {
        Dwarf_P_Debug bad_dbg = NULL;
        Dwarf_Error bad_err = NULL;

        res = dwarf_producer_init(
            DW_DLC_POINTER64 | DW_DLC_TARGET_LITTLEENDIAN |
                DW_DLC_SYMBOLIC_RELOCATIONS,
            section_callback,
            NULL, NULL, NULL,
            "not-an-isa",
            "V5",
            "",
            &bad_dbg,
            &bad_err);
        ASSERT(res == DW_DLV_ERROR && bad_err != NULL,
            "dwarf_producer_init() rejects unknown ISA with DW_DLV_ERROR");
    }

    if (g_failures) {
        printf("test_package: %d assertion(s) FAILED\n", g_failures);
        return EXIT_FAILURE;
    }
    printf("test_package: all libdwarfp producer assertions passed\n");
    return EXIT_SUCCESS;
}
