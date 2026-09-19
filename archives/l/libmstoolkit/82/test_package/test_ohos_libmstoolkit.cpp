#ifndef __OHOS__
#error "test_ohos_libmstoolkit must be compiled with the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "test_ohos_libmstoolkit requires the HarmonyOS PC AArch64 target"
#endif

#include <MSObject.h>
#include <MSReader.h>
#include <Spectrum.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <sys/stat.h>
#include <unistd.h>

int main()
{
    using namespace MSToolkit;

    const char* tmpdir = std::getenv("TMPDIR");
    if (tmpdir == NULL || tmpdir[0] == '\0') return 1;
    if (sizeof(void*) != 8) return 2;

    const std::string path = std::string(tmpdir) + "/libmstoolkit_ohos_" +
                             std::to_string(static_cast<int>(getpid())) + ".ms2";

    Spectrum source;
    source.setFileType(MS2);
    source.setScanNumber(82);
    source.setScanNumber(82, true);
    source.setMsLevel(2);
    source.setMZ(682.42);
    source.add(321.1234, 98.75f);

    MSObject object;
    object.add(source);
    MSReader writer;
    writer.setPrecisionMZ(4);
    writer.setPrecisionInt(2);
    writer.writeFile(path.c_str(), ms2, object);

    struct stat metadata;
    if (stat(path.c_str(), &metadata) != 0) return 3;
    if (metadata.st_size <= 0 || (metadata.st_mode & S_IRUSR) == 0) return 4;

    Spectrum restored;
    MSReader reader;
    const bool read_ok = reader.readFile(path.c_str(), restored, 82);
    std::remove(path.c_str());

    if (!read_ok || restored.size() != 1) return 5;
    if (restored.getScanNumber() != 82 || restored.getFileType() != MS2) return 6;
    if (std::fabs(restored.at(0).mz - 321.1234) > 0.001) return 7;
    if (std::fabs(restored.at(0).intensity - 98.75f) > 0.01f) return 8;

    std::cout << "HarmonyOS AArch64 libmstoolkit TMPDIR round-trip passed"
              << std::endl;
    return 0;
}
