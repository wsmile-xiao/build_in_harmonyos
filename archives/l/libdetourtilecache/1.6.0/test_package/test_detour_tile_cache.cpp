#include <cstdio>
#include <cstdlib>

#if defined(LIBDETOURTILECACHE_HARMONYOS)
#include <unistd.h>
#endif

#include "DetourStatus.h"
#include "DetourTileCache.h"

static int check_cache_lifecycle()
{
    dtTileCache* cache = dtAllocTileCache();
    if (!cache)
    {
        std::printf("CHECK-FAIL: cache allocation\n");
        return 1;
    }

    dtTileCacheParams params = {};
    params.cs = 0.3f;
    params.ch = 0.2f;
    params.width = 16;
    params.height = 16;
    params.walkableHeight = 2.0f;
    params.walkableRadius = 0.6f;
    params.walkableClimb = 0.9f;
    params.maxSimplificationError = 1.3f;
    params.maxTiles = 16;
    params.maxObstacles = 8;

    const dtStatus status = cache->init(&params, 0, 0, 0);
    const dtTileCacheParams* got = cache->getParams();
    const bool ok = !dtStatusFailed(status) && got && got->maxTiles == 16 &&
                    got->maxObstacles == 8 && cache->getTileCount() == 16 &&
                    cache->getObstacleCount() == 8;
    dtFreeTileCache(cache);
    std::printf("CHECK-%s: cache lifecycle\n", ok ? "OK" : "FAIL");
    return ok ? 0 : 1;
}

static int check_obstacle_lifecycle()
{
    dtTileCache* cache = dtAllocTileCache();
    if (!cache)
    {
        std::printf("CHECK-FAIL: obstacle cache allocation\n");
        return 1;
    }

    dtTileCacheParams params = {};
    params.cs = 0.3f;
    params.ch = 0.2f;
    params.width = 8;
    params.height = 8;
    params.walkableHeight = 2.0f;
    params.walkableRadius = 0.6f;
    params.walkableClimb = 0.9f;
    params.maxSimplificationError = 1.3f;
    params.maxTiles = 8;
    params.maxObstacles = 4;

    bool ok = !dtStatusFailed(cache->init(&params, 0, 0, 0));
    const float pos[3] = {1.0f, 0.0f, 2.0f};
    dtObstacleRef ref = 0;
    ok = ok && !dtStatusFailed(cache->addObstacle(pos, 0.5f, 2.0f, &ref)) && ref != 0;
    ok = ok && cache->getObstacleByRef(ref) != 0;
    ok = ok && !dtStatusFailed(cache->removeObstacle(ref));
    dtFreeTileCache(cache);
    std::printf("CHECK-%s: obstacle reference lifecycle\n", ok ? "OK" : "FAIL");
    return ok ? 0 : 1;
}

static int check_harmonyos_environment()
{
#if defined(LIBDETOURTILECACHE_HARMONYOS)
    const char* tmpdir = std::getenv("TMPDIR");
    const bool ok = tmpdir && *tmpdir && access(tmpdir, W_OK) == 0;
    std::printf("CHECK-%s: HarmonyOS writable TMPDIR\n", ok ? "OK" : "FAIL");
    return ok ? 0 : 1;
#else
    std::printf("CHECK-SKIP: HarmonyOS-only test\n");
    return 0;
#endif
}

int main()
{
    return check_cache_lifecycle() + check_obstacle_lifecycle() +
           check_harmonyos_environment();
}
