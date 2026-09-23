/*
 * OpenHMD 0.3.0 test_package — 上游 unittests 完整移植
 * 上游源码: tests/unittests/{main.c,quat.c,vec.c,highlevel.c,tests.h}
 *
 * 上游测试直接 include 内部头 openhmdi.h（-I src），本消费者测试将
 * 所需类型定义（vec3f/quatf，来自 src/omath.h）与内部数学函数原型
 * （libopenhmd.a 导出的全局符号，nm 验证: ovec3f_normalize_me 等 T 符号）
 * 原样复刻，测试数据与断言逐项对齐上游，确保测试保真。
 *
 * 测试清单（与上游 main.c 的 Test() 序列一致）:
 *   vec3f: normalize_me / get_length / get_angle / get_dot          (4)
 *   quatf: init_axis / get_rotated / get_dot / inverse / diff       (5)
 *   highlevel: open_close_device / open_close_many_devices          (2)
 * 共 11 个测试函数（上游另有多处数据循环断言，累计约 50 项 TAssert）。
 */

#include <stdio.h>
#include <stdbool.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>

#include <openhmd.h>

/* ---- 上游 src/omath.h 类型复刻（verbatim）---- */
typedef union {
	struct { float x, y, z; };
	float arr[3];
} vec3f;

typedef union {
	struct { float x, y, z, w; };
	float arr[4];
} quatf;

/* ---- 上游内部数学函数原型（libopenhmd.a 全局符号，omath.c）---- */
void ovec3f_normalize_me(vec3f* me);
float ovec3f_get_length(const vec3f* me);
float ovec3f_get_angle(const vec3f* me, const vec3f* vec);
float ovec3f_get_dot(const vec3f* me, const vec3f* vec);
void oquatf_init_axis(quatf* me, const vec3f* vec, float angle);
void oquatf_get_rotated(const quatf* me, const vec3f* vec, vec3f* out_vec);
float oquatf_get_dot(const quatf* me, const quatf* q);
void oquatf_inverse(quatf* me);
void oquatf_diff(const quatf* me, const quatf* q, quatf* out_q);

/* ---- 上游 tests.h 断言宏复刻 ---- */
#define TAssert(_v) if(!(_v)){ printf("\ntest failed: %s @ %s:%d\n", __func__, __FILE__, __LINE__); exit(1); }

static bool float_eq(float a, float b, float t)
{
	return fabsf(a - b) < t;
}

static bool vec3f_eq(vec3f v1, vec3f v2, float t)
{
	for(int i = 0; i < 3; i++)
		if(!float_eq(v1.arr[i], v2.arr[i], t)){
			printf("\nvec.arr[%d] == %f, expected %f\n", i, v1.arr[i], v2.arr[i]);
			return false;
		}
	return true;
}

static bool quatf_eq(quatf q1, quatf q2, float t)
{
	for(int i = 0; i < 4; i++)
		if(!float_eq(q1.arr[i], q2.arr[i], t)){
			printf("\nquat.arr[%d] == %f, expected %f\n", i, q1.arr[i], q2.arr[i]);
			return false;
		}
	return true;
}

/* ---- 上游 vec.c ---- */

static void test_ovec3f_normalize_me(void)
{
	vec3f v[][2] = {
		{ {{1, 0, 0}}, {{1, 0, 0}} },
		{ {{1, 2, 3}}, {{0.267261241912424, 0.534522483824849, 0.801783725737273}} },
		{ {{-7, 13, 22}}, {{-0.264197974633739, 0.490653381462658, 0.830336491706037}} },
		{ {{.1, .1, .1}}, {{0.577350269189626, 0.577350269189626, 0.577350269189626}} },
		{ {{0, 0, 0}}, {{0, 0, 0}} },
	};

	int sz = sizeof(vec3f) * 2;
	float t = 0.001;

	for(int i = 0; i < (int)(sizeof(v) / sz); i++){
		vec3f norm = v[i][0];
		ovec3f_normalize_me(&norm);
		TAssert(vec3f_eq(norm, v[i][1], t));
	}
}

static void test_ovec3f_get_length(void)
{
	typedef struct { vec3f vec; float f; } vec_float;
	vec_float vf[] = {
		{ {{0, 0, 0}}, 0},
		{ {{1, 0, 0}}, 1},
		{ {{1, 2, 0}}, 2.23606797749979},
		{ {{1, -2, 0}}, 2.23606797749979},
		{ {{1, 2, 3}}, 3.7416573867739413},
		{ {{-1, -2, -3}}, 3.7416573867739413},
	};

	int sz = sizeof(vec_float);
	float t = 0.001;

	for(int i = 0; i < (int)(sizeof(vf) / sz); i++){
		TAssert(float_eq(ovec3f_get_length(&vf[i].vec), vf[i].f, t));
	}
}

static void test_ovec3f_get_angle(void)
{
	typedef struct { vec3f v1, v2; float f; } vec2_float;
	vec2_float vf[] = {
		{ {{0, 0, 0}}, {{0, 0, 0}}, 0},
		{ {{1, 0, 0}}, {{0, 0, 0}}, 0},
		{ {{2, 4, 3}}, {{1, 2, 3}}, 0.33940126397005316},
		{ {{2, 4, 3}}, {{-1, 2, 3}}, 0.7311043352203973},
	};

	int sz = sizeof(vec2_float);
	float t = 0.001;

	for(int i = 0; i < (int)(sizeof(vf) / sz); i++){
		TAssert(float_eq(ovec3f_get_angle(&vf[i].v1, &vf[i].v2), vf[i].f, t));
	}
}

static void test_ovec3f_get_dot(void)
{
	typedef struct { vec3f v1, v2; float f; } vec2_float;
	vec2_float vf[] = {
		{ {{0, 0, 0}}, {{0, 0, 0}}, 0},
		{ {{1, 2, 3}}, {{-.30, 2, 25}}, 78.7},
		{ {{-1, -10000000, 3}}, {{-.30, 2, 25}}, -19999924.7},
	};

	int sz = sizeof(vec2_float);
	float t = 0.001;

	for(int i = 0; i < (int)(sizeof(vf) / sz); i++){
		TAssert(float_eq(ovec3f_get_dot(&vf[i].v1, &vf[i].v2), vf[i].f, t));
	}
}

/* ---- 上游 quat.c ---- */

static void test_oquatf_init_axis(void)
{
	typedef struct { vec3f v; float f; quatf q; } vec_float_quat;
	vec_float_quat list[] = {
		{ {{0, 0, 0}}, 0, {{0, 0, 0, 1}}},
		{ {{5, 12, 3}}, 1, {{0.1796723168488794, 0.43121356043731063, 0.10780339010932766, 0.8775825618903728}}},
		{ {{-2, -3, 3}}, 1, {{-0.2044277365391809, -0.30664160480877134, 0.30664160480877134, 0.8775825618903728}} },
		{ {{100, -3, 3}}, -300, {{0.7142339081165469, -0.021427017243496407, 0.021427017243496407, 0.6992508064783751}} },
	};

	int sz = sizeof(vec_float_quat);
	float t = 0.001;

	for(int i = 0; i < (int)(sizeof(list) / sz); i++){
		quatf q;
		oquatf_init_axis(&q, &list[i].v, list[i].f);
		TAssert(quatf_eq(q, list[i].q, t));
	}
}

static void test_oquatf_get_rotated(void)
{
	typedef struct { quatf q; vec3f v1, v2; } quat_vec2;
	quat_vec2 list[] = {
		{ {{0, 0, 0, 0}}, {{0, 0, 0}}, {{0, 0, 0}} },
		{ {{0, 0, 0, 0}}, {{1, 2, 3}}, {{0, 0, 0}} },
		{ {{0, 0, 0, 1}}, {{1, 2, 3}}, {{1, 2, 3}} },
		{ {{.4, .2, .1, 1}}, {{2, 1, 0}}, {{2.18, 1.59, 0.2}} },
		{ {{.4, .2, .1, -1}}, {{2, 1, 0}}, {{2.58, 0.79, 0.2}} },
	};

	int sz = sizeof(quat_vec2);
	float t = 0.001;

	for(int i = 0; i < (int)(sizeof(list) / sz); i++){
		vec3f vec;
		oquatf_get_rotated(&list[i].q, &list[i].v1, &vec);
		TAssert(vec3f_eq(vec, list[i].v2, t));
	}
}

static void test_oquatf_get_dot(void)
{
	typedef struct { quatf q1, q2; float f; } quat2_float;
	quat2_float list[] = {
		{ {{1, 2, 3, 1}}, {{4, 3, 2, .5}}, 16.5 },
	};

	int sz = sizeof(quat2_float);
	float t = 0.001;

	for(int i = 0; i < (int)(sizeof(list) / sz); i++){
		TAssert(float_eq(oquatf_get_dot(&list[i].q1, &list[i].q2), list[i].f, t));
	}
}

static void test_oquatf_inverse(void)
{
	typedef struct { quatf q1, q2; } quat2;
	quat2 list[] = {
		{ {{1, 2, 3, 1}}, {{-0.06666666666666667, -0.13333333333333333, -0.2, 0.06666666666666667}} },
	};

	int sz = sizeof(quat2);
	float t = 0.001;

	for(int i = 0; i < (int)(sizeof(list) / sz); i++){
		oquatf_inverse(&list[i].q1);
		TAssert(quatf_eq(list[i].q1, list[i].q2, t));
	}
}

static void test_oquatf_diff(void)
{
	typedef struct { quatf q1, q2, q3; } quat3;
	quat3 list[] = {
		{ {{1, 2, 3, 1}}, {{5, 3, 2, .1}}, {{0.660000, -0.680000, 0.580000, 1.140000}} },
	};

	int sz = sizeof(quat3);
	float t = 0.001;

	for(int i = 0; i < (int)(sizeof(list) / sz); i++){
		quatf q;
		oquatf_diff(&list[i].q1, &list[i].q2, &q);
		TAssert(quatf_eq(q, list[i].q3, t));
	}
}

/* ---- 上游 highlevel.c（公共 API）---- */

static void test_highlevel_open_close_device(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	TAssert(ctx);

	int num_devices = ohmd_ctx_probe(ctx);
	TAssert(num_devices > 0);

	/* dummy 设备总在列表末尾（上游 openhmd.c: add dummy driver last） */
	ohmd_device* hmd = ohmd_list_open_device(ctx, num_devices - 1);
	TAssert(hmd);

	int ret = ohmd_close_device(hmd);
	TAssert(ret == 0);

	ohmd_ctx_destroy(ctx);
}

static void test_highlevel_open_close_many_devices(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	TAssert(ctx);

	int num_devices = ohmd_ctx_probe(ctx);
	TAssert(num_devices > 0);

	ohmd_device* hmds[16];

	for(int i = 0; i < 8; i++){
		hmds[i] = ohmd_list_open_device(ctx, num_devices - 1);
		TAssert(hmds[i]);
	}

	for(int i = 4; i < 8; i++){
		int ret = ohmd_close_device(hmds[i]);
		TAssert(ret == 0);
	}

	for(int i = 4; i < 16; i++){
		hmds[i] = ohmd_list_open_device(ctx, num_devices - 1);
		TAssert(hmds[i]);
	}

	for(int i = 0; i < 16; i++){
		int ret = ohmd_close_device(hmds[i]);
		TAssert(ret == 0);
	}

	ohmd_ctx_destroy(ctx);
}

/* ---- 公共 API 版本/字符串验证（上游 simple.c 等价路径）---- */
static void test_public_api_version(void)
{
	ohmd_require_version(0, 3, 0);

	int major, minor, patch;
	ohmd_get_version(&major, &minor, &patch);
	TAssert(major == 0 && minor == 3 && patch == 0);

	/* ohmd_gets 字符串 API 冒烟（GLSL 着色器源码描述符，非空验证）*/
	const char* glsl = NULL;
	TAssert(ohmd_gets(OHMD_GLSL_DISTORTION_VERT_SRC, &glsl) == OHMD_S_OK);
	TAssert(glsl != NULL && glsl[0] != '\0');
}

static void test_public_api_probe_enumeration(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	TAssert(ctx);

	int num_devices = ohmd_ctx_probe(ctx);
	TAssert(num_devices > 0);

	/* dummy 驱动注册 3 个设备（HMD + 左右控制器）+ external 1 个 = >=4 */
	for(int i = 0; i < num_devices; i++){
		const char* vendor = ohmd_list_gets(ctx, i, OHMD_VENDOR);
		TAssert(vendor != NULL);
		int cls = -1;
		TAssert(ohmd_list_geti(ctx, i, OHMD_DEVICE_CLASS, &cls) == 0);
	}

	/* 打开 dummy HMD 读屏幕分辨率属性（dummy 驱动硬编码 1280x800，
	 * 属性直读不经融合线程 —— 确定性断言）*/
	ohmd_device* dev = ohmd_list_open_device(ctx, num_devices - 3); /* dummy 列表首位 = HMD Null Device */
	TAssert(dev);
	int hres = 0, vres = 0;
	TAssert(ohmd_device_geti(dev, OHMD_SCREEN_HORIZONTAL_RESOLUTION, &hres) == OHMD_S_OK);
	TAssert(ohmd_device_geti(dev, OHMD_SCREEN_VERTICAL_RESOLUTION, &vres) == OHMD_S_OK);
	TAssert(hres == 1280 && vres == 800);
	/* 控制器状态（dummy getf：OHMD_CONTROLS_STATE 返回 2 项）*/
	float ctrl[16] = {0};
	TAssert(ohmd_device_getf(dev, OHMD_CONTROLS_STATE, ctrl) == OHMD_S_OK);
	TAssert(ctrl[0] == .1f && ctrl[1] == 1.0f);
	TAssert(ohmd_close_device(dev) == 0);

	ohmd_ctx_destroy(ctx);
}

/* ---- main（对齐上游 main.c 的 Test() 序列并扩展公共 API 测试）---- */
#define Test(_t) printf("   "#_t); _t(); printf("%*sok\n", 50 - (int)strlen(#_t), "");

int main(void)
{
	printf("vec3f tests\n");
	Test(test_ovec3f_normalize_me);
	Test(test_ovec3f_get_length);
	Test(test_ovec3f_get_angle);
	Test(test_ovec3f_get_dot);
	printf("\n");

	printf("quatf tests\n");
	Test(test_oquatf_init_axis);
	Test(test_oquatf_get_rotated);
	Test(test_oquatf_get_dot);
	Test(test_oquatf_inverse);
	Test(test_oquatf_diff);
	printf("\n");

	printf("high level tests\n");
	Test(test_highlevel_open_close_device);
	Test(test_highlevel_open_close_many_devices);
	printf("\n");

	printf("public api tests\n");
	Test(test_public_api_version);
	Test(test_public_api_probe_enumeration);
	printf("\n");

	printf("all a-ok\n");
	return 0;
}
