// Consumer-side API validation for tinyply 3.0 on HarmonyOS PC.
// Exercises the real PLY write/read API: ascii + binary round-trips,
// header inspection, property requests, typed data buffers, list
// elements, and malformed-header rejection. Returns non-zero on any
// failed check.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>

#include "tinyply.h"

using namespace tinyply;

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(expr)                                                        \
    do {                                                                   \
        ++g_checks;                                                        \
        if (!(expr)) {                                                     \
            ++g_failed;                                                    \
            std::printf("CHECK FAILED (%s:%d): %s\n", __FILE__, __LINE__, \
                        #expr);                                            \
        }                                                                  \
    } while (0)

static std::string write_ply(bool binary)
{
    // 3 vertices (float32 x,y,z) + 2 triangular faces (uint32 list).
    std::vector<float> verts = {0.f, 0.f, 0.f, 1.f, 0.f, 0.f, 0.f, 1.f, 0.f};
    std::vector<uint32_t> faces = {0, 1, 2, 2, 1, 0};

    PlyFile file;
    file.add_properties_to_element("vertex", {"x", "y", "z"}, Type::FLOAT32,
                                   verts.size() / 3,
                                   reinterpret_cast<uint8_t*>(verts.data()),
                                   Type::INVALID, 0);
    file.add_properties_to_element("face", {"vertex_indices"}, Type::UINT32,
                                   faces.size() / 3,
                                   reinterpret_cast<uint8_t*>(faces.data()),
                                   Type::UINT8, 3);

    std::ostringstream oss;
    file.write(oss, binary);
    return oss.str();
}

int main()
{
    // ---- ascii round-trip ----
    const std::string ascii = write_ply(false);
    CHECK(ascii.rfind("ply", 0) == 0);  // 1: PLY signature present

    {
        std::istringstream iss(ascii);
        PlyFile file;
        CHECK(file.parse_header(iss));      // 2: ascii header parses
        CHECK(!file.is_binary_file());      // 3: format detected as ascii

        long long vertex_size = -1;
        for (const auto& e : file.get_elements()) {
            if (e.name == "vertex") {
                vertex_size = static_cast<long long>(e.size);
            }
        }
        CHECK(vertex_size == 3);          // 4: vertex element present with count 3

        auto vertices = file.request_properties_from_element("vertex", {"x", "y", "z"});
        file.read(iss);
        CHECK(vertices && vertices->count == 3);  // 5: read back 3 vertices
        const float* v = reinterpret_cast<const float*>(vertices->buffer.get_const());
        CHECK(v[3] == 1.0f && v[7] == 1.0f && v[8] == 0.0f);  // 6: values round-trip

        auto faces = file.request_properties_from_element("face", {"vertex_indices"});
        (void)faces;  // requested before read in a fresh parse below
    }

    // ---- binary round-trip ----
    const std::string bin = write_ply(true);
    {
        std::istringstream iss(bin);
        PlyFile file;
        CHECK(file.parse_header(iss) && file.is_binary_file());  // 7: binary header

        auto vertices = file.request_properties_from_element("vertex", {"x", "y", "z"});
        auto faces = file.request_properties_from_element("face", {"vertex_indices"});
        file.read(iss);
        CHECK(vertices && vertices->count == 3);  // 8: binary vertex count
        CHECK(faces && faces->count == 2 &&
              faces->buffer.size_bytes() == 6 * sizeof(uint32_t));  // 9: face list data
    }

    // ---- malformed header rejection ----
    {
        // tinyply 3.0 rejects malformed headers by throwing; accept either
        // a false return or an exception as rejection.
        bool rejected = false;
        try {
            std::istringstream garbage("this is not a ply file at all");
            PlyFile file;
            rejected = !file.parse_header(garbage);
        } catch (const std::exception&) {
            rejected = true;
        }
        CHECK(rejected);  // 10: malformed input rejected
    }

    std::printf("tinyply test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
