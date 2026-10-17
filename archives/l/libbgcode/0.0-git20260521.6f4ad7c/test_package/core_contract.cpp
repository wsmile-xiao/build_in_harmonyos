// core_contract.cpp — consumer test for the binarize + core APIs.
//
// Drives bgcode::binarize::Binarizer directly (set_enabled + initialize /
// append_gcode / finalize), then validates the produced file with the core
// reader (is_valid_binary_gcode + read_header). Any failed CHECK makes the
// process exit nonzero, so exit 0 means all 6 checks passed.
//
// Two upstream API facts shape this test (binarize.cpp @ 6f4ad7c):
// - Binarizer defaults to disabled (m_enabled=false); initialize() is a
//   no-op returning Success without capturing FILE*, so append_gcode()
//   then fails with WriteError on the null file handle. set_enabled(true)
//   is mandatory before initialize().
// - An enabled initialize() requires printer / print / slicer metadata
//   (MissingPrinterMetadata / MissingPrintMetadata / MissingSlicerMetadata
//   otherwise), populated here with one entry each before initialize().
#include <LibBGCode/binarize/binarize.hpp>
#include <LibBGCode/core/core.hpp>

#include <cstddef>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>

static int g_passed = 0;
static int g_failed = 0;

#define CHECK(cond, label)                                                     \
    do {                                                                       \
        if (cond) {                                                            \
            ++g_passed;                                                        \
            std::cout << "CHECK pass: " << label << "\n";                      \
        } else {                                                               \
            ++g_failed;                                                        \
            std::cout << "CHECK FAIL: " << label << "\n";                      \
        }                                                                      \
    } while (0)

int main() {
    const char *path = "core_contract_sample.bgcode";

    bgcode::binarize::BinarizerConfig config;
    config.checksum = bgcode::core::EChecksumType::CRC32;

    FILE *file = std::fopen(path, "wb");
    if (file == nullptr) {
        std::cout << "CHECK FAIL: cannot open output file\n";
        return 1;
    }
    bgcode::binarize::Binarizer binarizer;
    binarizer.set_enabled(true);
    binarizer.get_binary_data().printer_metadata.raw_data.emplace_back(
        "printer_model", "MINI");
    binarizer.get_binary_data().print_metadata.raw_data.emplace_back(
        "filament used [g]", "1.0");
    binarizer.get_binary_data().slicer_metadata.raw_data.emplace_back(
        "fill_density", "15%");
    const bgcode::core::EResult init_res =
        binarizer.initialize(*file, config);
    if (init_res != bgcode::core::EResult::Success) {
        std::cout << "DIAG binarizer initialize result: "
                  << static_cast<int>(init_res) << " ("
                  << bgcode::core::translate_result(init_res) << ")\n";
    }
    CHECK(init_res == bgcode::core::EResult::Success,
          "binarizer initialize");
    const bgcode::core::EResult append_res =
        binarizer.append_gcode("G1 X1 Y2 F3000\n");
    if (append_res != bgcode::core::EResult::Success) {
        std::cout << "DIAG binarizer append_gcode result: "
                  << static_cast<int>(append_res) << " ("
                  << bgcode::core::translate_result(append_res) << ")\n";
    }
    CHECK(append_res == bgcode::core::EResult::Success,
          "binarizer append_gcode");
    CHECK(binarizer.finalize() == bgcode::core::EResult::Success,
          "binarizer finalize");
    std::fclose(file);

    {
        std::ifstream in(path, std::ios::binary | std::ios::ate);
        const long size = in.good() ? static_cast<long>(in.tellg()) : -1;
        CHECK(size > 0, "bgcode output non-empty");
    }

    file = std::fopen(path, "rb");
    if (file == nullptr) {
        std::cout << "CHECK FAIL: cannot reopen output file\n";
        return 1;
    }
    std::byte verify_buffer[2048];
    CHECK(bgcode::core::is_valid_binary_gcode(*file, true, verify_buffer,
                                              sizeof(verify_buffer)) ==
              bgcode::core::EResult::Success,
          "core is_valid_binary_gcode");
    bgcode::core::FileHeader header;
    CHECK(bgcode::core::read_header(*file, header, nullptr) ==
              bgcode::core::EResult::Success,
          "core read_header");
    std::fclose(file);

    std::cout << "RESULT core_contract: " << g_passed << "/"
              << (g_passed + g_failed) << " passed\n";
    return g_failed == 0 ? 0 : 1;
}
