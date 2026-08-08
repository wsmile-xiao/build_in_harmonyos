#include "aces_Writer.h"
#include "aces_errors.h"

#include <cstdio>
#include <fstream>
#include <iostream>

namespace {

int fail(const char *message)
{
    std::cerr << message << '\n';
    return 1;
}

}  // namespace

int main()
{
    const char *output_path = "aces_container_smoke.aces";
    std::remove(output_path);

    aces_Writer writer;
    MetaWriteClip clip;
    clip.duration = 1;
    clip.outputRows = 1;
    clip.outputCols = 1;
    clip.hi = writer.getDefaultHeaderInfo();
    clip.outputFilenames.push_back(output_path);

    err rc = writer.configure(clip);
    if (rc != aces_ErrorNone) {
        return fail("configure failed");
    }

    DynamicMetadata metadata;
    metadata.imageIndex = 0;
    metadata.imageCounter = 1;
    metadata.capDate = "2026:08:06 00:00:00";
    metadata.uuid = "00000000-0000-0000-0000-000000000000";

    rc = writer.newImageObject(metadata);
    if (rc != aces_ErrorNone) {
        return fail("newImageObject failed");
    }

    halfBytes rgb_half_row[3] = {0x3c00, 0x3c00, 0x3c00};
    rc = writer.storeHalfRow(rgb_half_row, 0);
    if (rc != aces_ErrorNone) {
        return fail("storeHalfRow failed");
    }

    rc = writer.saveImageObject();
    if (rc != aces_ErrorNone) {
        return fail("saveImageObject failed");
    }

    IOstats stats = writer.stats();
    if (stats.bytesProcessed == 0) {
        return fail("bytesProcessed was zero");
    }

    std::ifstream file(output_path, std::ios::binary);
    if (!file) {
        return fail("output file was not created");
    }

    unsigned char magic[4] = {};
    file.read(reinterpret_cast<char *>(magic), sizeof(magic));
    if (file.gcount() != static_cast<std::streamsize>(sizeof(magic))) {
        return fail("output file is too small");
    }

    if (magic[0] != 0x76 || magic[1] != 0x2f || magic[2] != 0x31 || magic[3] != 0x01) {
        return fail("output file magic did not match ACES/OpenEXR");
    }

    std::cout << "aces_container smoke test passed\n";
    return 0;
}
