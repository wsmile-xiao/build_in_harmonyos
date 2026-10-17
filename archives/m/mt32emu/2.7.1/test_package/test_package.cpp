#include <mt32emu/c_interface/c_interface.h>
#include <mt32emu/globals.h>

#include <cstdio>
#include <cstring>

int main() {
    bool passed = true;
    const mt32emu_bit32u expected_int = MT32EMU_VERSION_INT(2, 7, 1);
    const mt32emu_bit32u actual_int = mt32emu_get_library_version_int();
    const char *const actual_string = mt32emu_get_library_version_string();

    if (actual_int != expected_int) {
        std::fprintf(
            stderr,
            "unexpected integer version: 0x%08x (expected 0x%08x)\n",
            static_cast<unsigned int>(actual_int),
            static_cast<unsigned int>(expected_int)
        );
        passed = false;
    }
    if (actual_string == nullptr || std::strcmp(actual_string, "2.7.1") != 0) {
        std::fprintf(
            stderr,
            "unexpected string version: %s\n",
            actual_string == nullptr ? "<null>" : actual_string
        );
        passed = false;
    }
    if (mt32emu_get_machine_ids(nullptr, 0) == 0) {
        std::fprintf(stderr, "supported machine inventory is empty\n");
        passed = false;
    }
    if (mt32emu_get_rom_ids(nullptr, 0, nullptr) == 0) {
        std::fprintf(stderr, "supported ROM inventory is empty\n");
        passed = false;
    }

    mt32emu_report_handler_i report_handler = {};
    mt32emu_context context = mt32emu_create_context(report_handler, nullptr);
    if (context == nullptr) {
        std::fprintf(stderr, "failed to create emulation context\n");
        return 1;
    }
    if (mt32emu_is_open(context) != MT32EMU_BOOL_FALSE) {
        std::fprintf(stderr, "new context unexpectedly reports an open synth\n");
        passed = false;
    }
    mt32emu_select_renderer_type(context, MT32EMU_RT_FLOAT);
    if (mt32emu_get_selected_renderer_type(context) != MT32EMU_RT_FLOAT) {
        std::fprintf(stderr, "renderer selection was not retained\n");
        passed = false;
    }
    if (mt32emu_open_synth(context) != MT32EMU_RC_MISSING_ROMS) {
        std::fprintf(stderr, "opening without ROMs did not report MT32EMU_RC_MISSING_ROMS\n");
        passed = false;
    }
    if (mt32emu_is_open(context) != MT32EMU_BOOL_FALSE) {
        std::fprintf(stderr, "failed open attempt changed synth state\n");
        passed = false;
    }
    mt32emu_free_context(context);

    if (!passed) {
        return 1;
    }

    std::printf("PASS mt32emu consumer version=%s context=validated\n", actual_string);
    return 0;
}
