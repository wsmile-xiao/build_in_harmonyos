#if !defined(__OHOS__)
#error "test_ohos.cpp must be compiled for HarmonyOS"
#endif

#include <cstdio>
#include <cstdlib>
#include <string>

#include "DetourCrowd.h"
#include "DetourNavMesh.h"

static bool check_ohos_temp_file_and_crowd()
{
    const char* tmpdir = std::getenv("TMPDIR");
    const std::string base = (tmpdir != nullptr && *tmpdir != '\0') ? tmpdir : "/data/local/tmp";
    const std::string path = base + "/libdetourcrowd-1.6.0-ohos-check.txt";

    FILE* output = std::fopen(path.c_str(), "wb");
    if (output == nullptr)
    {
        std::printf("OHOS-CHECK-FAIL: cannot create %s\n", path.c_str());
        return false;
    }
    const char marker[] = "libdetourcrowd-ohos";
    const size_t marker_size = sizeof(marker) - 1;
    const bool write_ok = std::fwrite(marker, 1, marker_size, output) == marker_size;
    std::fclose(output);

    char contents[sizeof(marker)] = {};
    FILE* input = std::fopen(path.c_str(), "rb");
    const bool read_ok = input != nullptr && std::fread(contents, 1, marker_size, input) == marker_size;
    if (input != nullptr)
    {
        std::fclose(input);
    }
    const bool remove_ok = std::remove(path.c_str()) == 0;

    dtNavMesh* mesh = dtAllocNavMesh();
    dtCrowd* crowd = dtAllocCrowd();
    dtNavMeshParams params = {};
    params.maxTiles = 1;
    params.maxPolys = 8;
    const bool navmesh_ok = mesh != nullptr && !dtStatusFailed(mesh->init(&params));
    const bool crowd_ok = crowd != nullptr && navmesh_ok && crowd->init(1, 0.5f, mesh);
    const bool passed = write_ok && read_ok && std::string(contents, marker_size) == marker &&
        remove_ok && crowd_ok;
    std::printf("%s: HarmonyOS TMPDIR file roundtrip and Crowd init\n",
                passed ? "OHOS-CHECK-OK" : "OHOS-CHECK-FAIL");

    dtFreeCrowd(crowd);
    dtFreeNavMesh(mesh);
    return passed;
}

int main()
{
    return check_ohos_temp_file_and_crowd() ? 0 : 1;
}
