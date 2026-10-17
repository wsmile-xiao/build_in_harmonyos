#include <cstdio>

#include "DetourCrowd.h"
#include "DetourNavMesh.h"

static bool check_crowd_lifecycle()
{
    dtNavMesh* mesh = dtAllocNavMesh();
    if (mesh == nullptr)
    {
        std::printf("CHECK-FAIL: navmesh allocation returned null\n");
        return false;
    }

    dtNavMeshParams mesh_params = {};
    mesh_params.tileWidth = 32.0f;
    mesh_params.tileHeight = 32.0f;
    mesh_params.maxTiles = 8;
    mesh_params.maxPolys = 256;
    if (dtStatusFailed(mesh->init(&mesh_params)))
    {
        std::printf("CHECK-FAIL: navmesh initialization failed\n");
        dtFreeNavMesh(mesh);
        return false;
    }

    dtCrowd* crowd = dtAllocCrowd();
    if (crowd == nullptr || !crowd->init(4, 0.6f, mesh))
    {
        std::printf("CHECK-FAIL: crowd allocation or initialization failed\n");
        dtFreeCrowd(crowd);
        dtFreeNavMesh(mesh);
        return false;
    }

    dtCrowdAgentParams params = {};
    params.radius = 0.3f;
    params.height = 1.8f;
    params.maxAcceleration = 8.0f;
    params.maxSpeed = 3.5f;
    params.collisionQueryRange = 3.0f;
    params.pathOptimizationRange = 30.0f;
    params.separationWeight = 2.0f;
    params.updateFlags = 0;
    params.obstacleAvoidanceType = 0;
    params.queryFilterType = 0;

    const float position[3] = {0.0f, 0.0f, 0.0f};
    const int agent_index = crowd->addAgent(position, &params);
    dtCrowdAgent* agent = crowd->getEditableAgent(agent_index);
    dtCrowdAgent* active_agents[1] = {};
    const int active_count = crowd->getActiveAgents(active_agents, 1);
    const float velocity[3] = {1.0f, 0.0f, 0.0f};
    const bool velocity_requested = crowd->requestMoveVelocity(agent_index, velocity);

    const bool passed = agent_index == 0 && agent != nullptr && agent->active &&
        crowd->getAgentCount() == 4 && active_count == 1 &&
        active_agents[0] == agent && velocity_requested;
    std::printf("%s: crowd alloc/init/agent API\n", passed ? "CHECK-OK" : "CHECK-FAIL");

    dtFreeCrowd(crowd);
    dtFreeNavMesh(mesh);
    return passed;
}

int main()
{
    if (!check_crowd_lifecycle())
    {
        return 1;
    }
    std::printf("libdetourcrowd consumer test: all 1 checks passed\n");
    return 0;
}
