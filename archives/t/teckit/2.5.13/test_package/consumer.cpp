// Consumer check for the packaged TECkit libraries.
//
// The upstream suite drives the command line tools.  This program is the
// complementary check that links the installed TECkit libraries, includes the
// public headers through the paths Conan publishes, and converts text with one
// of the compiled mappings that ships in the upstream test data.

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include <TECkit_Common.h>
#include <TECkit_Compiler.h>
#include <TECkit_Engine.h>

namespace {
int checks = 0;
int failures = 0;

void check(bool condition, const char* message)
{
    ++checks;
    if (condition) {
        std::printf("ok   - %s\n", message);
    } else {
        std::printf("FAIL - %s\n", message);
        ++failures;
    }
}

std::vector<Byte> read_file(const char* path)
{
    std::vector<Byte> data;
    std::FILE* file = std::fopen(path, "rb");
    if (file == NULL) {
        return data;
    }

    if (std::fseek(file, 0, SEEK_END) != 0) {
        std::fclose(file);
        return data;
    }
    long size = std::ftell(file);
    if (size <= 0 || std::fseek(file, 0, SEEK_SET) != 0) {
        std::fclose(file);
        return data;
    }

    data.resize(static_cast<std::size_t>(size));
    std::size_t used = std::fread(&data[0], 1, data.size(), file);
    std::fclose(file);
    if (used != data.size()) {
        data.clear();
    }
    return data;
}
}

int main(int argc, char** argv)
{
    check(TECkit_GetVersion() == kCurrentTECkitVersion,
          "engine version matches the public header");
    check(TECkit_GetCompilerVersion() == kCurrentTECkitVersion,
          "compiler version matches the public header");

    if (argc < 2) {
        check(false, "compiled mapping path was supplied");
        std::printf("TEST_PACKAGE_RESULT total=%d passed=%d failed=%d\n",
                    checks, checks - failures, failures);
        return EXIT_FAILURE;
    }

    std::vector<Byte> mapping = read_file(argv[1]);
    check(!mapping.empty(), "upstream compiled mapping is readable");
    if (mapping.empty()) {
        std::printf("TEST_PACKAGE_RESULT total=%d passed=%d failed=%d\n",
                    checks, checks - failures, failures);
        return EXIT_FAILURE;
    }

    UInt32 lhsFlags = 0;
    UInt32 rhsFlags = 0;
    TECkit_Status status = TECkit_GetMappingFlags(
        &mapping[0], static_cast<UInt32>(mapping.size()), &lhsFlags, &rhsFlags);
    check(status == kStatus_NoError
              && (lhsFlags & kFlags_Unicode) == 0
              && (rhsFlags & kFlags_Unicode) != 0,
          "mapping declares a byte to Unicode conversion");

    TECkit_Converter converter = NULL;
    status = TECkit_CreateConverter(
        &mapping[0], static_cast<UInt32>(mapping.size()), 1,
        kForm_Bytes, kForm_UTF8, &converter);
    check(status == kStatus_NoError && converter != NULL,
          "TECkit_CreateConverter accepts the packaged mapping");

    bool converted = false;
    if (converter != NULL) {
        const Byte input[] = {'u', 'p', 'k', 'd', 'u', '|', 'G', 'm', ':'};
        const Byte expected[] = {
            0xE1, 0x80, 0x80, 0xE1, 0x80, 0x85, 0xE1, 0x80, 0xAF,
            0xE1, 0x80, 0xAD, 0xE1, 0x80, 0x80, 0xE1, 0x80, 0x9B,
            0xE1, 0x80, 0xB9, 0xE1, 0x80, 0x9D, 0xE1, 0x80, 0xAC,
            0xE1, 0x80, 0xB8
        };
        Byte output[64];
        UInt32 inUsed = 0;
        UInt32 outUsed = 0;
        status = TECkit_ConvertBuffer(
            converter, input, sizeof(input), &inUsed,
            output, sizeof(output), &outUsed, 1);
        converted = status == kStatus_NoError
                    && inUsed == sizeof(input)
                    && outUsed == sizeof(expected)
                    && std::memcmp(output, expected, sizeof(expected)) == 0;
    }
    check(converted, "TECkit_ConvertBuffer produces the upstream reference text");

    bool disposed = false;
    if (converter != NULL) {
        disposed = TECkit_DisposeConverter(converter) == kStatus_NoError;
    }
    check(disposed, "converter is disposed cleanly");

    std::printf("TEST_PACKAGE_RESULT total=%d passed=%d failed=%d\n",
                checks, checks - failures, failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
