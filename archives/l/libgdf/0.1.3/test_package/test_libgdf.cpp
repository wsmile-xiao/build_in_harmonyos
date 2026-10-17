// Consumer test for libgdf 0.1.3 (OHOS): exercises the public Writer API.
// Creates an empty GDF file, verifies it exists with the expected 264-byte
// header size, checks the GDF_VERSION macro, and reopens the file with Reader.
// Exit code is decided by the assertions below (non-zero on first failure).
#include <GDF/Version.h>
#include <GDF/Writer.h>
#include <GDF/Reader.h>

#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <sys/stat.h>

static int checks = 0;

#define CHECK(cond)                                                  \
    do {                                                             \
        if (!(cond)) {                                               \
            std::fprintf(stderr, "FAILED: %s (line %d)\n", #cond, __LINE__); \
            return 1;                                                \
        }                                                            \
        ++checks;                                                    \
    } while (0)

static bool file_exists(const std::string &path) {
    std::ifstream f(path.c_str(), std::ios_base::in);
    if (f.fail()) {
        return false;
    }
    f.close();
    return true;
}

static size_t file_size(const std::string &path) {
    struct stat st;
    if (stat(path.c_str(), &st) != 0) {
        return 0;
    }
    return static_cast<size_t>(st.st_size);
}

int main() {
    const std::string testfile = "test_libgdf_tmp.gdf";

    // 1) Version macro matches the adapted upstream release.
    CHECK(std::string(GDF_VERSION) == "0.1.3");

    // 2) Writer creates an empty GDF file (264 bytes: 256 main + 8 event header).
    std::remove(testfile.c_str());
    {
        gdf::Writer w;
        w.setEventSamplingRate(100);
        try {
            w.open(testfile);
        } catch (gdf::exception::header_issues &e) {
            if (e.num_errors() > 0) {
                throw;
            }
        }
        CHECK(w.isOpen());
        w.close();
        CHECK(!w.isOpen());
    }
    CHECK(file_exists(testfile));
    CHECK(file_size(testfile) == 264);

    // 3) Reader reopens the file produced by Writer.
    {
        gdf::Reader r;
        r.open(testfile);
        r.close();
    }
    ++checks;

    std::remove(testfile.c_str());

    std::printf("test_libgdf: %d checks passed\n", checks);
    return 0;
}
