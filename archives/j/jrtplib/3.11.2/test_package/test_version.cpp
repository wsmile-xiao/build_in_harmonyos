#include <jrtplib3/rtplibraryversion.h>
#include <jrtplib3/rtperrors.h>
#include <jrtplib3/rtptimeutilities.h>

#include <cmath>
#include <iostream>
#include <string>

namespace {

int s_failures = 0;

void check(bool ok, const char *name)
{
    std::cout << (ok ? "[PASS] " : "[FAIL] ") << name << std::endl;
    if (!ok) {
        ++s_failures;
    }
}

} // namespace

int main()
{
    const jrtplib::RTPLibraryVersion version = jrtplib::RTPLibraryVersion::GetVersion();
    const std::string versionString = version.GetVersionString();
    std::cout << "jrtplib version: " << versionString << std::endl;

    check(!versionString.empty(), "version-string-nonempty");
    check(versionString.find("3.11.2") == 0, "version-string-is-3.11.2");
    check(version.GetMajorNumber() == 3, "version-major-is-3");
    check(version.GetMinorNumber() == 11, "version-minor-is-11");
    check(version.GetDebugNumber() == 2, "version-debug-is-2");

    const std::string outOfMem = jrtplib::RTPGetErrorString(ERR_RTP_OUTOFMEM);
    const std::string notCreated = jrtplib::RTPGetErrorString(ERR_RTP_SESSION_NOTCREATED);
    std::cout << "ERR_RTP_OUTOFMEM: " << outOfMem << std::endl;
    std::cout << "ERR_RTP_SESSION_NOTCREATED: " << notCreated << std::endl;
    check(!outOfMem.empty(), "error-string-outofmem-nonempty");
    check(!notCreated.empty() && notCreated != outOfMem, "error-strings-distinct");

    const jrtplib::RTPTime stamp(1, 500000);
    check(stamp.GetSeconds() == 1, "rtptime-seconds");
    check(stamp.GetMicroSeconds() == 500000, "rtptime-microseconds");
    check(std::fabs(stamp.GetDouble() - 1.5) < 1e-9, "rtptime-double-roundtrip");

    if (s_failures != 0) {
        std::cerr << s_failures << " check(s) failed" << std::endl;
        return 1;
    }
    std::cout << "test_version: all 10 checks passed" << std::endl;
    return 0;
}
