#include <smpeg2/smpeg.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

int main() {
    SMPEG_version version{};
    SMPEG_VERSION(&version);
    if (version.major != 2 || version.minor != 0 || version.patch != 0) {
        std::fprintf(
            stderr,
            "Unexpected smpeg2 version: %u.%u.%u\n",
            static_cast<unsigned>(version.major),
            static_cast<unsigned>(version.minor),
            static_cast<unsigned>(version.patch)
        );
        return 1;
    }

    char invalid_data[] = "not an mpeg stream";
    SMPEG_Info info{};
    SMPEG *mpeg = SMPEG_new_data(
        invalid_data,
        static_cast<int>(std::strlen(invalid_data)),
        &info,
        0
    );
    if (mpeg == nullptr) {
        std::fprintf(stderr, "SMPEG_new_data returned null for invalid-data probe\n");
        return 1;
    }

    const SMPEGstatus status = SMPEG_status(mpeg);
    SMPEG_delete(mpeg);
    if (status != SMPEG_ERROR && status != SMPEG_STOPPED) {
        std::fprintf(stderr, "Unexpected status for invalid-data probe: %d\n", status);
        return 1;
    }

    std::puts("smpeg2 API and invalid-data probe: PASS");
    return 0;
}
