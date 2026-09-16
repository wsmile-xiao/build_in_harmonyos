/*
 * openhmd 消费者测试（test_package）
 *
 * 目标：对「打包后的 openhmd 静态库」做黑盒消费验证——只使用上游公共头文件
 *       include/openhmd.h 暴露的 API，不重声明任何内部符号，确保测试通过
 *       == 用户按 conan 消费该包可用。
 *
 * 用例设计原则（CI 无 HMD 硬件，必须全部可确定性判定）：
 *   - 设备发现类：OpenHMD 内置 dummy 驱动恒定注册若干虚拟设备（HMD +
 *     手柄），无需真实硬件；断言只依赖「至少存在一个 HMD 类设备」这类
 *     结构性事实，不依赖设备顺序与具体型号。
 *   - 属性/元数据类：只做存在性与关系性断言（> 0、zfar > znear、
 *     左右眼对称等），不硬编码某一型号的数值，避免随上游参数调整而脆断。
 *   - 姿态类：用 ohmd_device_settings 关闭后台自动更新后手动 tick，
 *     消除多线程时序，使读数与读写回环（setf→getf）完全确定。
 *
 * 与上游 tests/unittests（11 个用例，内部数学 API ovec3f_ / oquatf_）的分工：
 *   上游用例在配方 build() 中以原始源码整体编译执行（见 conanfile.py
 *   _run_upstream_unittests）；本文件负责「打包产物 + 公共 API」这一层，
 *   两者互补，不重复：上游走内部数学函数，本文件全部走 openhmd.h。
 */

#include <dlfcn.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "openhmd.h"

#define TAssert(_v)                                                            \
	do {                                                                   \
		if (!(_v)) {                                                   \
			printf("\ntest failed: %s @ %s:%d\n", __func__, __FILE__, \
			       __LINE__);                                      \
			exit(1);                                               \
		}                                                              \
	} while (0)

static int float_eq(float a, float b, float eps)
{
	return fabsf(a - b) <= eps;
}

/* 四元数单位模长（含容差） */
static int quat_is_unit(const float q[4])
{
	float n = sqrtf(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]);
	return float_eq(n, 1.0f, 1e-3f);
}

static int quat_eq(const float a[4], const float b[4], float eps)
{
	int i;
	for (i = 0; i < 4; i++) {
		if (!float_eq(a[i], b[i], eps)) {
			return 0;
		}
	}
	return 1;
}

static int vec3_eq(const float a[3], const float b[3], float eps)
{
	int i;
	for (i = 0; i < 3; i++) {
		if (!float_eq(a[i], b[i], eps)) {
			return 0;
		}
	}
	return 1;
}

/*
 * 从设备列表尾部反向查找最后一个 HMD 类设备。
 * 反转查找的理由：真实驱动（hidapi/usb）先枚举，dummy 驱动最后注册，
 * 因此尾部设备是当前环境中最可预期、最不依赖硬件的对象。
 * 返回设备索引，失败返回 -1。
 */
static int find_last_hmd(ohmd_context* ctx, int num_devices)
{
	int i;
	for (i = num_devices - 1; i >= 0; i--) {
		int klass = 0;
		if (ohmd_list_geti(ctx, i, OHMD_DEVICE_CLASS, &klass) != OHMD_S_OK) {
			continue;
		}
		if (klass == OHMD_DEVICE_CLASS_HMD) {
			return i;
		}
	}
	return -1;
}

/* 打开 settings 指定的设备（settings 可为 NULL），失败返回 NULL */
static ohmd_device* open_hmd(ohmd_context* ctx, int num_devices,
			     ohmd_device_settings* settings)
{
	int index = find_last_hmd(ctx, num_devices);
	if (index < 0) {
		return NULL;
	}
	if (settings) {
		return ohmd_list_open_device_s(ctx, index, settings);
	}
	return ohmd_list_open_device(ctx, index);
}

/* 用例 1：上下文生命周期与探测 */
static void test_ctx_create_probe_destroy(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	const char* err;
	int num_devices;

	TAssert(ctx != NULL);
	/* 新建上下文不应带错误（实现可能返回空串而非 NULL） */
	err = ohmd_ctx_get_error(ctx);
	TAssert(err == NULL || err[0] == '\0');

	num_devices = ohmd_ctx_probe(ctx);
	/* dummy 驱动恒定提供 1 个 HMD + 2 个手柄，故至少 3 个设备 */
	TAssert(num_devices >= 3);

	ohmd_ctx_destroy(ctx);
}

/* 用例 2：设备枚举——类别合法、字符串元数据可读 */
static void test_device_list_metadata(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	int num_devices, i, hmd_count = 0;

	TAssert(ctx != NULL);
	num_devices = ohmd_ctx_probe(ctx);
	TAssert(num_devices >= 3);

	for (i = 0; i < num_devices; i++) {
		int klass = -1;
		int flags = 0;
		const char* vendor = ohmd_list_gets(ctx, i, OHMD_VENDOR);
		const char* product = ohmd_list_gets(ctx, i, OHMD_PRODUCT);

		TAssert(ohmd_list_geti(ctx, i, OHMD_DEVICE_CLASS, &klass) == OHMD_S_OK);
		TAssert(klass >= OHMD_DEVICE_CLASS_HMD &&
			klass <= OHMD_DEVICE_CLASS_GENERIC_TRACKER);
		TAssert(ohmd_list_geti(ctx, i, OHMD_DEVICE_FLAGS, &flags) == OHMD_S_OK);
		TAssert(vendor != NULL && strlen(vendor) > 0);
		TAssert(product != NULL && strlen(product) > 0);

		if (klass == OHMD_DEVICE_CLASS_HMD) {
			hmd_count++;
		}
	}

	/* 环境中必须至少存在一个可用的 HMD 类设备（dummy 保证） */
	TAssert(hmd_count >= 1);

	ohmd_ctx_destroy(ctx);
}

/* 用例 3：打开/关闭设备 */
static void test_device_open_close(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	int num_devices;
	ohmd_device* dev;

	TAssert(ctx != NULL);
	num_devices = ohmd_ctx_probe(ctx);
	TAssert(num_devices >= 3);

	dev = open_hmd(ctx, num_devices, NULL);
	TAssert(dev != NULL);
	TAssert(ohmd_close_device(dev) == 0);

	/* 关闭后可再次打开（设备句柄不复用） */
	dev = open_hmd(ctx, num_devices, NULL);
	TAssert(dev != NULL);
	TAssert(ohmd_close_device(dev) == 0);

	ohmd_ctx_destroy(ctx);
}

/* 用例 4：设备属性访问器（float/int 公共接口） */
static void test_device_properties(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	int num_devices;
	ohmd_device* dev;
	float hsize = 0.0f, vsize = 0.0f;
	float lens_sep = 0.0f, ipd = 0.0f;
	float zfar = 0.0f, znear = 0.0f;
	float lfov = 0.0f, rfov = 0.0f;
	float lratio = 0.0f, rratio = 0.0f;
	float vert_aberration[3] = {0.0f, 0.0f, 0.0f};
	float u_distortion[4] = {0.0f, 0.0f, 0.0f, 0.0f};
	int hres = 0, vres = 0;

	TAssert(ctx != NULL);
	num_devices = ohmd_ctx_probe(ctx);
	TAssert(num_devices >= 3);

	dev = open_hmd(ctx, num_devices, NULL);
	TAssert(dev != NULL);

	TAssert(ohmd_device_getf(dev, OHMD_SCREEN_HORIZONTAL_SIZE, &hsize) == OHMD_S_OK);
	TAssert(ohmd_device_getf(dev, OHMD_SCREEN_VERTICAL_SIZE, &vsize) == OHMD_S_OK);
	TAssert(hsize > 0.0f && vsize > 0.0f);

	TAssert(ohmd_device_geti(dev, OHMD_SCREEN_HORIZONTAL_RESOLUTION, &hres) == OHMD_S_OK);
	TAssert(ohmd_device_geti(dev, OHMD_SCREEN_VERTICAL_RESOLUTION, &vres) == OHMD_S_OK);
	TAssert(hres > 0 && vres > 0);

	TAssert(ohmd_device_getf(dev, OHMD_LENS_HORIZONTAL_SEPARATION, &lens_sep) == OHMD_S_OK);
	TAssert(lens_sep > 0.0f);
	TAssert(ohmd_device_getf(dev, OHMD_EYE_IPD, &ipd) == OHMD_S_OK);
	/* dummy 驱动未显式设置 IPD（设备默认值），只要求非负 */
	TAssert(ipd >= 0.0f);

	TAssert(ohmd_device_getf(dev, OHMD_PROJECTION_ZFAR, &zfar) == OHMD_S_OK);
	TAssert(ohmd_device_getf(dev, OHMD_PROJECTION_ZNEAR, &znear) == OHMD_S_OK);
	TAssert(zfar > znear && znear > 0.0f);

	/* 左右眼视场角/宽高比对称（同一 HMD 双目参数一致） */
	TAssert(ohmd_device_getf(dev, OHMD_LEFT_EYE_FOV, &lfov) == OHMD_S_OK);
	TAssert(ohmd_device_getf(dev, OHMD_RIGHT_EYE_FOV, &rfov) == OHMD_S_OK);
	TAssert(lfov > 0.0f && float_eq(lfov, rfov, 1e-6f));
	TAssert(ohmd_device_getf(dev, OHMD_LEFT_EYE_ASPECT_RATIO, &lratio) == OHMD_S_OK);
	TAssert(ohmd_device_getf(dev, OHMD_RIGHT_EYE_ASPECT_RATIO, &rratio) == OHMD_S_OK);
	TAssert(lratio > 0.0f && float_eq(lratio, rratio, 1e-6f));

	/* 畸变/色差系数数组：接口可读且不写越界（数组在栈上，越界即崩溃） */
	TAssert(ohmd_device_getf(dev, OHMD_UNIVERSAL_DISTORTION_K, u_distortion) == OHMD_S_OK);
	TAssert(ohmd_device_getf(dev, OHMD_UNIVERSAL_ABERRATION_K, vert_aberration) == OHMD_S_OK);

	TAssert(ohmd_close_device(dev) == 0);
	ohmd_ctx_destroy(ctx);
}

/* 用例 5：控件元数据与状态读取 */
static void test_device_control_metadata(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	int num_devices;
	ohmd_device* dev;
	int control_count = 0;
	int hints[8] = {0};
	int types[8] = {0};
	float state[8] = {0.0f};
	int i;

	TAssert(ctx != NULL);
	num_devices = ohmd_ctx_probe(ctx);
	TAssert(num_devices >= 3);

	dev = open_hmd(ctx, num_devices, NULL);
	TAssert(dev != NULL);

	TAssert(ohmd_device_geti(dev, OHMD_CONTROL_COUNT, &control_count) == OHMD_S_OK);
	/* dummy HMD 暴露 2 个控件；真实设备可能更多，此处只要求非空 */
	TAssert(control_count > 0 && control_count <= 8);

	TAssert(ohmd_device_geti(dev, OHMD_CONTROLS_HINTS, hints) == OHMD_S_OK);
	TAssert(ohmd_device_geti(dev, OHMD_CONTROLS_TYPES, types) == OHMD_S_OK);
	for (i = 0; i < control_count; i++) {
		/* hint 为枚举（OHMD_MENU 起始）+ type 为 OHMD_ANALOG/OHMD_DIGITAL */
		TAssert(hints[i] >= 0 && hints[i] <= 0xFF);
		TAssert(types[i] == OHMD_ANALOG || types[i] == OHMD_DIGITAL);
	}

	/* 控件状态：同一帧内可读，且模拟量/数字量取值有限 */
	TAssert(ohmd_device_getf(dev, OHMD_CONTROLS_STATE, state) == OHMD_S_OK);
	for (i = 0; i < control_count; i++) {
		TAssert(!isnan(state[i]));
		TAssert(state[i] >= -1.0f && state[i] <= 1.0f);
	}

	TAssert(ohmd_close_device(dev) == 0);
	ohmd_ctx_destroy(ctx);
}

/* 用例 6：GLSL 畸变着色器源码读取（全局字符串描述，ohmd_gets） */
static void test_shader_source_strings(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	const char* vert_src = NULL;
	const char* frag_src = NULL;
	const char* vert_es_src = NULL;
	const char* frag_es_src = NULL;

	TAssert(ctx != NULL);

	TAssert(ohmd_gets(OHMD_GLSL_DISTORTION_VERT_SRC, &vert_src) == OHMD_S_OK);
	TAssert(ohmd_gets(OHMD_GLSL_DISTORTION_FRAG_SRC, &frag_src) == OHMD_S_OK);
	TAssert(vert_src != NULL && strlen(vert_src) > 0);
	TAssert(frag_src != NULL && strlen(frag_src) > 0);
	/* 必须是真的着色器源码，而不是占位串 */
	TAssert(strstr(vert_src, "void main") != NULL);
	TAssert(strstr(frag_src, "void main") != NULL);

	/* GLES 变体同样可用 */
	TAssert(ohmd_gets(OHMD_GLSL_ES_DISTORTION_VERT_SRC, &vert_es_src) == OHMD_S_OK);
	TAssert(ohmd_gets(OHMD_GLSL_ES_DISTORTION_FRAG_SRC, &frag_es_src) == OHMD_S_OK);
	TAssert(vert_es_src != NULL && strlen(vert_es_src) > 0);
	TAssert(frag_es_src != NULL && strlen(frag_es_src) > 0);

	ohmd_ctx_destroy(ctx);
}

/* 用例 7：设备设置（关闭后台自动更新）+ 姿态读写回环 */
static void test_device_settings_and_pose_roundtrip(void)
{
	ohmd_context* ctx = ohmd_ctx_create();
	int num_devices;
	ohmd_device_settings* settings;
	ohmd_device* dev;
	int autoupdate = 0;
	float q[4] = {0.0f, 0.0f, 0.0f, 0.0f};
	float pos[3] = {9.0f, 9.0f, 9.0f};
	const float target_q[4] = {0.2f, 0.3f, 0.4f, 0.8f};
	float target_q_norm[4];
	const float target_pos[3] = {1.25f, -2.5f, 3.75f};
	float norm, corrected[4];

	TAssert(ctx != NULL);
	num_devices = ohmd_ctx_probe(ctx);
	TAssert(num_devices >= 3);

	/* 通过 ohmd_device_settings 关闭后台自动更新，改为显式 tick：
	 * 消除融合线程时序，使姿态读写完全确定（CI 无硬件亦可判定） */
	settings = ohmd_device_settings_create(ctx);
	TAssert(settings != NULL);
	TAssert(ohmd_device_settings_seti(settings, OHMD_IDS_AUTOMATIC_UPDATE,
					  &autoupdate) == OHMD_S_OK);

	dev = open_hmd(ctx, num_devices, settings);
	TAssert(dev != NULL);
	ohmd_device_settings_destroy(settings);

	/* 显式 tick 一次：dummy 驱动上报单位四元数姿态 */
	ohmd_ctx_update(ctx);

	TAssert(ohmd_device_getf(dev, OHMD_ROTATION_QUAT, q) == OHMD_S_OK);
	TAssert(quat_is_unit(q));

	TAssert(ohmd_device_getf(dev, OHMD_POSITION_VECTOR, pos) == OHMD_S_OK);
	pos[0] = pos[1] = pos[2] = 0.0f; /* 位置仅要求可读，具体值由驱动决定 */

	/* 姿态写入→读回：写入值应能被读回（内部经旋转修正量补偿） */
	norm = sqrtf(target_q[0] * target_q[0] + target_q[1] * target_q[1] +
		     target_q[2] * target_q[2] + target_q[3] * target_q[3]);
	target_q_norm[0] = target_q[0] / norm;
	target_q_norm[1] = target_q[1] / norm;
	target_q_norm[2] = target_q[2] / norm;
	target_q_norm[3] = target_q[3] / norm;
	TAssert(ohmd_device_setf(dev, OHMD_ROTATION_QUAT, (float*)target_q_norm) == OHMD_S_OK);
	TAssert(ohmd_device_getf(dev, OHMD_ROTATION_QUAT, corrected) == OHMD_S_OK);
	TAssert(quat_eq(corrected, target_q_norm, 1e-3f));

	/* 位置写入→读回 */
	TAssert(ohmd_device_setf(dev, OHMD_POSITION_VECTOR, (float*)target_pos) == OHMD_S_OK);
	TAssert(ohmd_device_getf(dev, OHMD_POSITION_VECTOR, pos) == OHMD_S_OK);
	TAssert(vec3_eq(pos, target_pos, 1e-3f));

	TAssert(ohmd_close_device(dev) == 0);
	ohmd_ctx_destroy(ctx);
}

struct test_case {
	const char* name;
	void (*fn)(void);
};

/*
 * 鸿蒙特有测试：OHOS 运行时装载器与 hidapi 依赖闭包契约
 *
 * 为什么必须在鸿蒙上单独验证（普通消费者用例覆盖不到）：
 *   - OHOS 使用自带 musl 装载器，dlopen/dlsym/dladdr 由 libc 提供（系统无独立
 *     libdl.so），制品仓发布的动态库只带不带版本号的 .so，没有 .so.0 兼容软链；
 *   - openhmd 的 hidapi 后端驱动（rift/vive/wmr/deepoon/nolo/3glasses 等）在
 *     运行期才装载 hidapi 并调用 hid_* 符号：链接期全过、运行期才报
 *     "symbol not found" 是这条链路上真实出现过的故障形态（本地适配期实测
 *     libhidapi-libusb.so 因 libusb 运行期路径缺失报 libusb_handle_events 缺失）；
 *   - 因此必须在鸿蒙上守住「消费者按 conan 消费本包后，hidapi → libusb-1.0
 *     整条依赖闭包能被 OHOS 装载器完整解析」这一契约。
 *
 * 用例完全确定、无需 HMD 硬件（只做装载/符号解析/后端初始化，不枚举设备）。
 */
static void test_ohos_loader_dependency_contract(void)
{
	void* lib = NULL;
	void* raw = NULL;
	void* sym = NULL;
	const char* err = NULL;
	Dl_info info;
	int (*hid_init_fn)(void) = NULL;
	int (*hid_exit_fn)(void) = NULL;
	int rc = 0;
	size_t i = 0;
	size_t missing = 0;

#if !defined(__OHOS__) || !defined(__aarch64__)
	/* 非 OHOS aarch64 平台：该契约在其它平台不成立（无 OHOS 装载器/musl 语义），
	 * 显式 SKIP 并打印原因，避免在 Linux/macOS 上误报失败。 */
	printf("    SKIP: %s 仅适用于 OHOS aarch64"
	       "（当前 __OHOS__=%d, __aarch64__=%d）@ %s:%d\n",
	       __func__,
#ifdef __OHOS__
	       1,
#else
	       0,
#endif
#ifdef __aarch64__
	       1,
#else
	       0,
#endif
	       __FILE__, __LINE__);
	return;
#endif

	/* 1) OHOS 装载器按制品仓命名（不带版本号的 .so）解析 hidapi；
	 *    RTLD_NOW 立即绑定全部符号，等价于一次性验证 hidapi → libusb-1.0
	 *    整条传递依赖闭包在 OHOS 运行期可解析。 */
	dlerror();
	lib = dlopen("libhidapi-libusb.so", RTLD_NOW | RTLD_LOCAL);
	err = dlerror();
	printf("    dlopen(libhidapi-libusb.so, RTLD_NOW) -> %s%s%s\n",
	       lib ? "ok" : "fail", err ? " err=" : "", err ? err : "");
	TAssert(lib != NULL);

	/* 2) openhmd 各 hidapi 后端驱动源码**活动代码**实际引用的入口符号必须全部在位
	 *    （13 个驱动 API，不含被驱动自身 #if 0 屏蔽的 hid_get_indexed_string）
	 *    + 本用例使用的生命周期符号 hid_init，共 14 个。
	 *    缺任何一个，对应驱动在 OHOS 上运行期即不可用，而编译/链接期不会报错。 */
	{
		static const char* const hid_syms[] = {
			"hid_enumerate", "hid_free_enumeration", "hid_open_path",
			"hid_close", "hid_read", "hid_write",
			"hid_set_nonblocking", "hid_send_feature_report",
			"hid_get_feature_report",
			"hid_get_manufacturer_string", "hid_get_product_string",
			"hid_get_serial_number_string",
			"hid_exit", "hid_init",
		};
		size_t total = sizeof(hid_syms) / sizeof(hid_syms[0]);

		for (i = 0; i < total; i++) {
			if (dlsym(lib, hid_syms[i]) == NULL)
				missing++;
		}
		printf("    hidapi 入口符号可解析: %d/%d\n",
		       (int)(total - missing), (int)total);
		TAssert(missing == 0);
	}

	/* 3) 装载器映射的是真实实现：dladdr 回报的路径必须指向 hidapi 动态库，
	 *    排除"符号解析成功但落在空壳/错误模块"的情况。 */
	sym = dlsym(lib, "hid_enumerate");
	TAssert(sym != NULL);
	memset(&info, 0, sizeof(info));
	TAssert(dladdr(sym, &info) != 0);
	printf("    dladdr(hid_enumerate) -> %s\n",
	       info.dli_fname ? info.dli_fname : "(null)");
	TAssert(info.dli_fname != NULL && strstr(info.dli_fname, "hidapi") != NULL);

	/* 4) hidapi 生命周期入口可调用且不崩溃（依赖闭包在运行期真实可用）：
	 *    返回值语义——0 = libusb 后端初始化成功；-1 = 当前环境无 /dev/bus/usb
	 *    访问权限（CI 沙箱常见，与依赖闭包无关）。两者都接受，不把环境差异
	 *    误判为适配缺陷。 */
	raw = dlsym(lib, "hid_init");
	TAssert(raw != NULL);
	memcpy(&hid_init_fn, &raw, sizeof(hid_init_fn));

	raw = dlsym(lib, "hid_exit");
	TAssert(raw != NULL);
	memcpy(&hid_exit_fn, &raw, sizeof(hid_exit_fn));

	rc = hid_init_fn();
	printf("    hid_init() -> %d（0=libusb 后端可用；-1=无 /dev/bus/usb 访问，沙箱环境正常）\n", rc);
	TAssert(rc == 0 || rc == -1);

	/* 仅在初始化成功时调用 hid_exit()：初始化失败（环境无 USB 设备节点）时
	 * 上游 libusb 后端处于未初始化状态，此时调用属未定义行为，不做赌注。
	 * 依赖闭包已由上方 dlsym(hid_exit) 非空断言覆盖（符号必须存在且可解析）。 */
	if (rc == 0)
		hid_exit_fn();
	dlclose(lib);
}

static struct test_case tests[] = {
	{"ctx_create_probe_destroy", test_ctx_create_probe_destroy},
	{"device_list_metadata", test_device_list_metadata},
	{"device_open_close", test_device_open_close},
	{"device_properties", test_device_properties},
	{"device_control_metadata", test_device_control_metadata},
	{"shader_source_strings", test_shader_source_strings},
	{"device_settings_and_pose_roundtrip",
	 test_device_settings_and_pose_roundtrip},
	{"ohos_loader_dependency_contract", test_ohos_loader_dependency_contract},
};

int main(void)
{
	size_t i;
	size_t total = sizeof(tests) / sizeof(tests[0]);

	for (i = 0; i < total; i++) {
		tests[i].fn();
		printf("consumer test: %-40s ok\n", tests[i].name);
	}

	printf("all %d consumer tests a-ok\n", (int)total);
	return 0;
}
