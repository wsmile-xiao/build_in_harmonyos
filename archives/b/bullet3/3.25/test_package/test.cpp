// bullet3/3.25 — Conan L1 consumer test (test_package)
//
// 实质调用被测包发布物（6 个静态库 + include/bullet）的公开 API，逐用例计数并汇总；
// 任一用例失败 → main 返回非 0 → conan create 判负（R34：禁止空壳测试）。
//
// 用例清单（输出同名）：
//   1. physics_rigidbody_fall              —— 刚体动力学仿真（BulletDynamics/BulletCollision/LinearMath）
//   2. collision_contact_detection         —— 离散碰撞检测 + 接触流形（BulletCollision）
//   3. serialization_default_serializer    —— 世界序列化（LinearMath btSerializer）
//   4. task_scheduler_parallel_for_api     —— 任务调度器 API + btParallelFor（LinearMath btThreads）
//   5. softbody_rope_simulation            —— 软体绳索仿真（BulletSoftBody）
//   6. ohos_platform_abi            【鸿蒙特有】—— __OHOS__ 宏 + 64 位 ABI + btScalar 精度
//   7. ohos_precision_contract      【鸿蒙特有】—— OHOS 通用回退平台分支 + ABI 精度契约
//
// 说明：本包按上游默认构建（BT_THREADSAFE=0 / BULLET2_MULTITHREADING=OFF），
//       btParallelFor 走顺序回退实现；用例 4 只校验该 API 面与结果正确性。

#include <btBulletCollisionCommon.h>
#include <btBulletDynamicsCommon.h>
#include <BulletSoftBody/btDefaultSoftBodySolver.h>
#include <BulletSoftBody/btSoftBodyHelpers.h>
#include <BulletSoftBody/btSoftBodyRigidBodyCollisionConfiguration.h>
#include <BulletSoftBody/btSoftRigidDynamicsWorld.h>
#include <LinearMath/btSerializer.h>
#include <LinearMath/btThreads.h>

#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>

static int g_pass = 0;
static int g_fail = 0;
static char g_detail[512];

static void setDetail(const char* fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(g_detail, sizeof(g_detail), fmt, ap);
	va_end(ap);
}

// ── 用例 1：刚体动力学（球体落地）────────────────────────────────────────
static bool case_physics_rigidbody_fall()
{
	btDbvtBroadphase broadphase;
	btDefaultCollisionConfiguration collisionConfig;
	btCollisionDispatcher dispatcher(&collisionConfig);
	btSequentialImpulseConstraintSolver solver;
	btDiscreteDynamicsWorld world(&dispatcher, &broadphase, &solver, &collisionConfig);
	world.setGravity(btVector3(0, -10, 0));

	btStaticPlaneShape groundShape(btVector3(0, 1, 0), 0);
	btDefaultMotionState groundMS(btTransform(btQuaternion(0, 0, 0, 1), btVector3(0, 0, 0)));
	btRigidBody::btRigidBodyConstructionInfo groundCI(0, &groundMS, &groundShape, btVector3(0, 0, 0));
	btRigidBody ground(groundCI);
	world.addRigidBody(&ground);

	btSphereShape sphereShape(1.0);
	btDefaultMotionState sphereMS(btTransform(btQuaternion(0, 0, 0, 1), btVector3(0, 10, 0)));
	btRigidBody::btRigidBodyConstructionInfo sphereCI(1.0, &sphereMS, &sphereShape, btVector3(0, 0, 0));
	btRigidBody sphere(sphereCI);
	world.addRigidBody(&sphere);

	for (int i = 0; i < 180; i++)
		world.stepSimulation(btScalar(1.0 / 60.0), 10);

	btTransform trans;
	sphere.getMotionState()->getWorldTransform(trans);
	btScalar y = trans.getOrigin().getY();
	setDetail("sphere rest y=%.4f (expect ~1.0, radius=1, ground y=0)", (double)y);
	return std::fabs((double)y - 1.0) < 0.05;
}

// ── 用例 2：离散碰撞检测 + 接触流形 ──────────────────────────────────────
static bool case_collision_contact_detection()
{
	btDefaultCollisionConfiguration cfg;
	btCollisionDispatcher dispatcher(&cfg);
	btDbvtBroadphase broadphase;
	btCollisionWorld world(&dispatcher, &broadphase, &cfg);

	btSphereShape s1(1.0);
	btSphereShape s2(1.0);
	btCollisionObject o1;
	btCollisionObject o2;
	o1.setCollisionShape(&s1);
	o2.setCollisionShape(&s2);

	btTransform t;
	t.setIdentity();
	t.setOrigin(btVector3(0, 0, 0));
	o1.setWorldTransform(t);
	t.setOrigin(btVector3(1.5f, 0, 0));
	o2.setWorldTransform(t);
	world.addCollisionObject(&o1);
	world.addCollisionObject(&o2);

	world.performDiscreteCollisionDetection();

	int manifolds = dispatcher.getNumManifolds();
	int contacts = 0;
	for (int i = 0; i < manifolds; i++)
		contacts += dispatcher.getManifoldByIndexInternal(i)->getNumContacts();

	setDetail("manifolds=%d contactPoints=%d (expect >=1 contact)", manifolds, contacts);
	return (manifolds >= 1) && (contacts >= 1);
}

// ── 用例 3：btDefaultSerializer 世界序列化 ───────────────────────────────
static bool case_serialization_default_serializer()
{
	btDbvtBroadphase broadphase;
	btDefaultCollisionConfiguration cfg;
	btCollisionDispatcher dispatcher(&cfg);
	btSequentialImpulseConstraintSolver solver;
	btDiscreteDynamicsWorld world(&dispatcher, &broadphase, &solver, &cfg);
	world.setGravity(btVector3(0, -9.8f, 0));

	btSphereShape shape(0.5f);
	btRigidBody::btRigidBodyConstructionInfo ci(1.0f, 0, &shape, btVector3(0, 0, 0));
	btRigidBody body(ci);
	world.addRigidBody(&body);

	btDefaultSerializer serializer;
	world.serialize(&serializer);

	const unsigned char* buf = serializer.getBufferPointer();
	int len = serializer.getCurrentBufferSize();
	setDetail("serialized %d bytes (buffer=%s)", len, buf ? "non-null" : "NULL");
	return (len > 0) && (buf != 0);
}

// ── 用例 4：任务调度器 API + btParallelFor ───────────────────────────────
struct ArrayFillBody : public btIParallelForBody
{
	int* data;
	void forLoop(int iBegin, int iEnd) const BT_OVERRIDE
	{
		for (int i = iBegin; i < iEnd; i++)
			data[i] = i * 3 + 1;
	}
};

static bool case_task_scheduler_parallel_for_api()
{
	if (btGetTaskScheduler() == 0)
		btSetTaskScheduler(btCreateDefaultTaskScheduler());
	if (btGetTaskScheduler() == 0)
		btSetTaskScheduler(btGetSequentialTaskScheduler());

	btITaskScheduler* ts = btGetTaskScheduler();
	if (ts == 0)
	{
		setDetail("btGetTaskScheduler() == NULL");
		return false;
	}

	const int N = 4096;
	int data[N];
	for (int i = 0; i < N; i++)
		data[i] = -1;

	ArrayFillBody body;
	body.data = data;
	btParallelFor(0, N, 64, body);

	int wrong = 0;
	for (int i = 0; i < N; i++)
		if (data[i] != i * 3 + 1)
			wrong++;

#if BT_THREADSAFE
	const int threadsafe = 1;
#else
	const int threadsafe = 0;
#endif

	setDetail("scheduler='%s' numThreads=%d BT_THREADSAFE=%d wrong=%d/%d",
			  ts->getName(), ts->getNumThreads(), threadsafe, wrong, N);
	return (wrong == 0) && (std::strlen(ts->getName()) > 0);
}

// ── 用例 5：软体（BulletSoftBody）────────────────────────────────────────
static bool case_softbody_rope_simulation()
{
	btSoftBodyRigidBodyCollisionConfiguration sbCfg;
	btCollisionDispatcher dispatcher(&sbCfg);
	btDbvtBroadphase broadphase;
	btSequentialImpulseConstraintSolver solver;
	btDefaultSoftBodySolver softSolver;
	btSoftRigidDynamicsWorld world(&dispatcher, &broadphase, &solver, &sbCfg, &softSolver);
	world.setGravity(btVector3(0, -9.8f, 0));

	btSoftBody* rope = btSoftBodyHelpers::CreateRope(
		world.getWorldInfo(), btVector3(0, 10, 0), btVector3(0, 0, 0), 10, 1);
	if (rope == 0)
	{
		setDetail("CreateRope() returned NULL");
		return false;
	}
	world.addSoftBody(rope, 1, -1);

	for (int i = 0; i < 60; i++)
		world.stepSimulation(btScalar(1.0 / 60.0), 1);

	int nodes = rope->m_nodes.size();
	btScalar fixedEndY = (nodes > 0) ? rope->m_nodes[0].m_x.getY() : -999.0f;
	btScalar freeEndY = (nodes > 0) ? rope->m_nodes[nodes - 1].m_x.getY() : -999.0f;
	setDetail("rope nodes=%d fixed-end y=%.4f free-end y=%.4f (free end must hang below fixed end)",
			  nodes, (double)fixedEndY, (double)freeEndY);
	// 绳索首节点固定 y=10，自由端在重力下下垂（初始 y=0）
	return (nodes >= 11) && (std::fabs((double)fixedEndY - 10.0) < 0.5) && (freeEndY < 9.5f);
}

// ── 用例 6【鸿蒙特有】：OHOS 平台识别 + ABI ──────────────────────────────
static bool case_ohos_platform_abi()
{
#if defined(__OHOS__)
	const int isOhos = 1;
#else
	const int isOhos = 0;
#endif
#if defined(__aarch64__)
	const int isAarch64 = 1;
#else
	const int isAarch64 = 0;
#endif

	setDetail("__OHOS__=%d __aarch64__=%d sizeof(void*)=%d sizeof(btScalar)=%d",
			  isOhos, isAarch64, (int)sizeof(void*), (int)sizeof(btScalar));
	return (isOhos == 1) && (isAarch64 == 1) && (sizeof(void*) == 8) && (sizeof(btScalar) == 4);
}

// ── 用例 7【鸿蒙特有】：精度/平台分支契约 ────────────────────────────────
static bool case_ohos_precision_contract()
{
#ifdef BT_USE_DOUBLE_PRECISION
	const int doublePrecision = 1;
#else
	const int doublePrecision = 0;
#endif
#if defined(_LINUX) || defined(_WIN32) || defined(__APPLE__)
	const int genericFallback = 0;
#else
	const int genericFallback = 1;
#endif

	setDetail("BT_USE_DOUBLE_PRECISION=%d (package=float) genericPlatformFallback=%d",
			  doublePrecision, genericFallback);
	// 包为单精度静态库：消费者必须看到同一精度（否则 btScalar ABI 错配）；
	// OHOS 不定义 _LINUX/__APPLE__/_WIN32，走 bullet 的通用回退代码路径。
	return (doublePrecision == 0) && (genericFallback == 1);
}

// ── 运行器 ──────────────────────────────────────────────────────────────
struct TestCase
{
	const char* name;
	bool (*fn)();
};

int main()
{
	static const TestCase cases[] = {
		{"physics_rigidbody_fall", &case_physics_rigidbody_fall},
		{"collision_contact_detection", &case_collision_contact_detection},
		{"serialization_default_serializer", &case_serialization_default_serializer},
		{"task_scheduler_parallel_for_api", &case_task_scheduler_parallel_for_api},
		{"softbody_rope_simulation", &case_softbody_rope_simulation},
		{"ohos_platform_abi", &case_ohos_platform_abi},
		{"ohos_precision_contract", &case_ohos_precision_contract},
	};
	const int total = (int)(sizeof(cases) / sizeof(cases[0]));

	std::printf("==== bullet3/3.25 test_package (consumer view) ====\n");
	for (int i = 0; i < total; i++)
	{
		g_detail[0] = '\0';
		bool ok = cases[i].fn();
		if (ok)
		{
			g_pass++;
			std::printf("[ OK ] %-34s %s\n", cases[i].name, g_detail);
		}
		else
		{
			g_fail++;
			std::printf("[FAILED] %-32s %s\n", cases[i].name, g_detail);
		}
	}
	std::printf("---- total=%d passed=%d failed=%d skipped=0 ----\n", total, g_pass, g_fail);
	return (g_fail == 0) ? 0 : 1;
}
