#include <cstdio>
#include <cmath>
#include "recastnavigation/DetourNavMesh.h"
#include "recastnavigation/Recast.h"

int main()
{
    // Use the Recast API to prove the core library is linkable.
    rcContext ctx(true);
    ctx.enableLog(true);
    ctx.enableTimer(true);

    // Use the Detour API to prove the Detour component is linkable.
    dtNavMeshParams params;
    params.tileWidth = 10.0f;
    params.tileHeight = 10.0f;
    params.maxTiles = 8;
    params.maxPolys = 32;
    std::printf("tile dims: %.1f x %.1f, maxTiles=%d\n",
                params.tileWidth, params.tileHeight, params.maxTiles);

    float d = rcSqrt(16.0f);
    if (std::fabs(d - 4.0f) > 1e-5f) {
        return 1;
    }
    std::printf("recastnavigation OK: rcSqrt(16)=%.1f\n", d);
    return 0;
}
