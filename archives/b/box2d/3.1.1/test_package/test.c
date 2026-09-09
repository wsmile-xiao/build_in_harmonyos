// test_package 消费者验证 — 调用 box2d 公共 C API 验证包可用（R34: 实质依赖被测包）
#include <stdio.h>
#include <math.h>
#include <box2d/box2d.h>

int main(void) {
	// 创建世界并做一次步进，验证链接与运行时可用性
	b2WorldDef worldDef = b2DefaultWorldDef();
	worldDef.gravity = (b2Vec2){0.0f, -10.0f};
	b2WorldId worldId = b2CreateWorld(&worldDef);
	if (!b2World_IsValid(worldId)) {
		printf("FAIL: b2CreateWorld\n");
		return 1;
	}

	b2BodyDef bodyDef = b2DefaultBodyDef();
	bodyDef.type = b2_dynamicBody;
	bodyDef.position = (b2Vec2){0.0f, 1.0f};
	b2BodyId bodyId = b2CreateBody(worldId, &bodyDef);

	b2ShapeDef shapeDef = b2DefaultShapeDef();
	b2Circle circle = {0};
	circle.radius = 0.5f;
	b2ShapeId shapeId = b2CreateCircleShape(bodyId, &shapeDef, &circle);
	if (!b2Shape_IsValid(shapeId)) {
		printf("FAIL: b2CreateCircleShape\n");
		return 1;
	}

	b2World_Step(worldId, 1.0f / 60.0f, 4);
	b2Vec2 pos = b2Body_GetPosition(bodyId);
	printf("box2d 3.1.1 consumer test: position after 1 step = (%.3f, %.3f)\n", pos.x, pos.y);
	if (!(fabs(pos.x) < 1e-4f) || !(pos.y < 1.0f)) {
		printf("FAIL: physics step result\n");
		return 1;
	}

	b2DestroyWorld(worldId);
	printf("box2d 3.1.1 consumer test: OK\n");
	return 0;
}
