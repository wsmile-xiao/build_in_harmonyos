#include <MSObject.h>
#include <MSReader.h>
#include <Spectrum.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>

#if !defined(_WIN32)
#include <unistd.h>
#endif

namespace {

bool close_to(double actual, double expected, double tolerance)
{
    return std::fabs(actual - expected) <= tolerance;
}

std::string temporary_path()
{
    const char* directory = std::getenv("TMPDIR");
    if (directory == NULL || directory[0] == '\0') directory = ".";
#if defined(_WIN32)
    const int process_id = 1;
#else
    const int process_id = static_cast<int>(getpid());
#endif
    return std::string(directory) + "/libmstoolkit_consumer_" +
           std::to_string(process_id) + ".ms2";
}

}  // namespace

int main()
{
    using namespace MSToolkit;

    Spectrum source;
    source.setFileType(MS2);
    source.setScanNumber(42);
    source.setScanNumber(42, true);
    source.setMsLevel(2);
    source.setRTime(3.5f);
    source.setMZ(445.34);
    source.add(100.25, 12.5f);
    source.add(200.50, 25.0f);

    MSObject spectra;
    spectra.add(source);
    if (spectra.size() != 1 || spectra.at(0).size() != 2) return 1;

    const std::string path = temporary_path();
    MSReader writer;
    writer.setPrecisionMZ(4);
    writer.setPrecisionInt(2);
    writer.writeFile(path.c_str(), ms2, spectra);

    Spectrum restored;
    MSReader reader;
    const bool read_ok = reader.readFile(path.c_str(), restored, 42);
    std::remove(path.c_str());

    if (!read_ok) return 2;
    if (restored.getScanNumber() != 42 || restored.getFileType() != MS2) return 3;
    if (restored.size() != 2) return 4;
    if (!close_to(restored.at(0).mz, 100.25, 0.001) ||
        !close_to(restored.at(0).intensity, 12.5, 0.01)) return 5;
    if (!close_to(restored.at(1).mz, 200.50, 0.001) ||
        !close_to(restored.at(1).intensity, 25.0, 0.01)) return 6;

    std::cout << "libmstoolkit consumer round-trip passed" << std::endl;
    return 0;
}
