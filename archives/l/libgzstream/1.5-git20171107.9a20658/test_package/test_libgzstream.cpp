#include <gzstream.h>

#include <cstdio>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>

#ifndef __OHOS__
#error "This test verifies the HarmonyOS/OHOS package build"
#endif

namespace {

bool check(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << '\n';
        return false;
    }
    return true;
}

}  // namespace

int main() {
    const char* path = "libgzstream-ohos-roundtrip.gz";
    const std::string payload("HarmonyOS PC\0libgzstream\n", 25);
    bool passed = true;

    {
        ogzstream output(path);
        passed &= check(output.good(), "ogzstream opens an output file");
        output.write(payload.data(), static_cast<std::streamsize>(payload.size()));
        output.close();
        passed &= check(output.good(), "ogzstream writes and closes cleanly");
    }

    {
        std::ifstream gzip_file(path, std::ios::binary);
        unsigned char magic[2] = {0, 0};
        gzip_file.read(reinterpret_cast<char*>(magic), 2);
        passed &= check(
            gzip_file.gcount() == 2 && magic[0] == 0x1f && magic[1] == 0x8b,
            "output has the gzip magic bytes");
    }

    std::string restored;
    {
        igzstream input(path);
        passed &= check(input.good(), "igzstream opens the generated gzip file");
        restored.assign(
            std::istreambuf_iterator<char>(input),
            std::istreambuf_iterator<char>());
        input.close();
    }
    passed &= check(restored == payload, "binary payload survives gzip round trip");

    if (std::remove(path) != 0) {
        std::perror("remove");
        return 1;
    }
    if (!passed) {
        return 1;
    }
    std::cout << "HarmonyOS libgzstream consumer test: PASS\n";
    return 0;
}
