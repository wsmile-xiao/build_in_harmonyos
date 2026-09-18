#include <cmath>
#include <cstdio>

#include "DetourCommon.h"
#include "DetourNavMesh.h"
#include "DetourNavMeshQuery.h"
#include "DetourStatus.h"

static int check_navmesh_lifecycle()
{
    dtNavMesh* mesh = dtAllocNavMesh();
    if (mesh == nullptr)
    {
        std::printf("CHECK-FAIL: navmesh alloc returned null\n");
        return 1;
    }
    dtNavMeshParams params = {};
    params.tileWidth = 32.0f;
    params.tileHeight = 32.0f;
    params.maxTiles = 8;
    params.maxPolys = 256;
    dtStatus status = mesh->init(&params);
    if (dtStatusFailed(status))
    {
        std::printf("CHECK-FAIL: navmesh init failed status=%u\n", status);
        dtFreeNavMesh(mesh);
        return 1;
    }
    const dtNavMeshParams* got = mesh->getParams();
    if (got == nullptr || got->maxTiles != 8 || got->maxPolys != 256)
    {
        std::printf("CHECK-FAIL: navmesh params mismatch\n");
        dtFreeNavMesh(mesh);
        return 1;
    }
    dtFreeNavMesh(mesh);
    std::printf("CHECK-OK: navmesh lifecycle (alloc/init/params/free)\n");
    return 0;
}

static int check_convex_poly_sample()
{
    const float pts[] = {
        0.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f,
        1.0f, 0.0f, 0.0f,
    };
    float areas[6] = {0};
    float out[3] = {0};
    dtRandomPointInConvexPoly(pts, 3, areas, 0.5f, 1.0f, out);
    if (std::fabs(out[0] - 0.5f) > 1e-4f || std::fabs(out[1]) > 1e-4f || std::fabs(out[2] - 0.5f) > 1e-4f)
    {
        std::printf("CHECK-FAIL: convex poly sample got %.4f %.4f %.4f\n", out[0], out[1], out[2]);
        return 1;
    }
    std::printf("CHECK-OK: random point in convex poly (0.5,0,0.5)\n");
    return 0;
}

static int check_query_and_vector_helpers()
{
    dtNavMeshQuery* query = dtAllocNavMeshQuery();
    if (query == nullptr)
    {
        std::printf("CHECK-FAIL: query alloc returned null\n");
        return 1;
    }
    dtFreeNavMeshQuery(query);

    const float v1[3] = {1.0f, 2.0f, 3.0f};
    const float v2[3] = {4.0f, 5.0f, 6.0f};
    float dest[3] = {0};
    dtVadd(dest, v1, v2);
    if (std::fabs(dest[0] - 5.0f) > 1e-5f || std::fabs(dest[1] - 7.0f) > 1e-5f || std::fabs(dest[2] - 9.0f) > 1e-5f)
    {
        std::printf("CHECK-FAIL: dtVadd mismatch\n");
        return 1;
    }
    float dist = dtVdist(v1, v2);
    if (std::fabs(dist - std::sqrt(27.0f)) > 1e-4f)
    {
        std::printf("CHECK-FAIL: dtVdist mismatch %.5f\n", dist);
        return 1;
    }
    std::printf("CHECK-OK: query alloc/free and vector helpers (vadd/vdist)\n");
    return 0;
}

int main()
{
    int failures = 0;
    failures += check_navmesh_lifecycle();
    failures += check_convex_poly_sample();
    failures += check_query_and_vector_helpers();
    if (failures != 0)
    {
        std::printf("libdetour consumer test: %d check(s) failed\n", failures);
        return 1;
    }
    std::printf("libdetour consumer test: all 3 checks passed\n");
    return 0;
}
