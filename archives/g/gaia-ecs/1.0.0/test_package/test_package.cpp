// test_package.cpp — gaia-ecs 1.0.0 消费者验证
// 真实调用 gaia ECS API：World 创建实体、挂载组件、更新与查询生命周期。
#include <gaia.h>

#include <cstdint>
#include <cstdio>

struct Position {
    float x, y, z;
};

struct Velocity {
    float x, y, z;
};

int main() {
    gaia::ecs::World world;

    // 创建实体并挂载组件
    const auto e = world.add();
    if (!world.has(e)) {
        std::printf("FAIL: entity not created\n");
        return 1;
    }
    world.add<Position>(e, {1.0f, 2.0f, 3.0f});
    world.add<Velocity>(e, {0.1f, 0.2f, 0.3f});

    if (!world.has<Position>(e) || !world.has<Velocity>(e)) {
        std::printf("FAIL: component not added\n");
        return 2;
    }

    // 读取组件值
    {
        const auto& p = world.get<Position>(e);
        if (p.x != 1.0f || p.y != 2.0f || p.z != 3.0f) {
            std::printf("FAIL: component value mismatch\n");
            return 3;
        }
    }

    // 更新世界（触发系统/内部同步）
    world.update();

    // 删除组件与实体
    world.del<Position>(e);
    if (world.has<Position>(e)) {
        std::printf("FAIL: component not removed\n");
        return 4;
    }
    world.del(e);
    world.update();

    std::printf("test gaia-ecs 1.0.0: OK\n");
    return 0;
}