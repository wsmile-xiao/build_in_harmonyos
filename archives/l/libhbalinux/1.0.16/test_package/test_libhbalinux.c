/*
 * test_libhbalinux.c — 消费者视角验证 libhbalinux/1.0.16（仅使用安装后的产物）
 *
 * 验证面 1..7：SNIA HBAAPI vendor 库的真实调用路径
 *   libHBAAPI 会 dlopen 本 vendor 库并调用其导出的 HBA_RegisterLibraryV2()，
 *   由本库把 HBA_* 处理函数表填回调用方，之后 libHBAAPI 再调用这些 handler。
 *   这里完整复刻该契约（注册 → 填充 → 调用 handler），而不是只打印字符串。
 *
 * 验证面 8..9：OHOS 平台契约
 *   - vendor 库必须能在 OHOS 上被 dlopen（libHBAAPI 通过 /etc/hba.conf 动态加载）
 *   - OHOS 无 /sys/class/fc_host 时，适配器计数必须为 0 且不崩溃（不误报适配器）
 *
 * 说明：先包含 <time.h>，上游 hbaapi.h 使用了 struct tm 但未自行包含该头
 *       （libhbaapi/2.2.9 记录的上游怪癖）。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#include <hbaapi.h>
#include <vendorhbaapi.h>

/* vendor 库导出的注册入口（由 libhbalinux.so 提供） */
extern HBA_STATUS HBA_RegisterLibrary(HBA_ENTRYPOINTS *ep);
extern HBA_STATUS HBA_RegisterLibraryV2(HBA_ENTRYPOINTSV2 *ep);

static int failed;
static int passed;
static int skipped;

static void check(int condition, const char *name)
{
	if (condition) {
		passed++;
		printf("[PASS] %s\n", name);
	} else {
		failed++;
		printf("[FAIL] %s\n", name);
	}
}

static void skip(const char *name, const char *why)
{
	skipped++;
	printf("[SKIP] %s (%s)\n", name, why);
}

int main(void)
{
	HBA_ENTRYPOINTSV2 epsv2;
	HBA_ENTRYPOINTS epsv1;
	char adapter_name[64] = { 0 };
	HBA_UINT32 version;
	HBA_UINT32 adapters;
	HBA_HANDLE handle;
	HBA_STATUS status;
	void *self;
	void *sym;
	struct stat st;

	printf("== libhbalinux consumer test (HBAAPI v%d) ==\n", HBA_LIBVERSION);

	/* 1. vendor 库注册入口：填回 HBA_* 处理函数表（libHBAAPI 的实际调用路径） */
	memset(&epsv2, 0, sizeof(epsv2));
	status = HBA_RegisterLibraryV2(&epsv2);
	check(status == HBA_STATUS_OK
	      && epsv2.GetVersionHandler != NULL
	      && epsv2.LoadLibraryHandler != NULL
	      && epsv2.GetNumberOfAdaptersHandler != NULL
	      && epsv2.OpenAdapterHandler != NULL
	      && epsv2.FreeLibraryHandler != NULL,
	      "case1 HBA_RegisterLibraryV2 fills the entry-point table");

	/* 2. 版本 handler 返回本库支持的 HBAAPI 版本 */
	version = epsv2.GetVersionHandler ? epsv2.GetVersionHandler() : 0;
	printf("     HBA_GetVersion -> %u (expect %d)\n", version, HBA_LIBVERSION);
	check(version == HBA_LIBVERSION, "case2 GetVersionHandler() == HBA_LIBVERSION");

	/* 3. LoadLibrary handler：adapter_init() 扫描 /sys/class/fc_host */
	status = epsv2.LoadLibraryHandler ? epsv2.LoadLibraryHandler() : HBA_STATUS_ERROR;
	check(status == HBA_STATUS_OK, "case3 LoadLibraryHandler() == HBA_STATUS_OK");

	/* 4. 适配器计数：OHOS 上没有 FC 适配器时为 0 */
	adapters = epsv2.GetNumberOfAdaptersHandler ? epsv2.GetNumberOfAdaptersHandler() : 1;
	printf("     HBA_GetNumberOfAdapters -> %u\n", adapters);
	if (stat("/sys/class/fc_host", &st) != 0) {
		check(adapters == 0,
		      "case4 no FC adapter reported when /sys/class/fc_host is absent");
	} else {
		skip("case4 adapter count",
		     "/sys/class/fc_host exists on this host, count is environment dependent");
	}

	/* 5. 越界索引必须被拒绝（HBA_STATUS_ERROR_ILLEGAL_INDEX） */
	status = epsv2.GetAdapterNameHandler
		 ? epsv2.GetAdapterNameHandler(adapters, adapter_name)
		 : HBA_STATUS_OK;
	printf("     HBA_GetAdapterName(%u) -> %d\n", adapters, (int)status);
	check(status != HBA_STATUS_OK,
	      "case5 GetAdapterNameHandler() rejects an out-of-range index");

	/* 6. 打开不存在的适配器返回无效句柄（0） */
	handle = epsv2.OpenAdapterHandler ? epsv2.OpenAdapterHandler("hba0") : 0;
	check(handle == 0, "case6 OpenAdapterHandler(\"hba0\") yields no handle");

	/* 7. FreeLibrary handler：adapter_shutdown() + adapter_destroy_all() */
	status = epsv2.FreeLibraryHandler ? epsv2.FreeLibraryHandler() : HBA_STATUS_ERROR;
	check(status == HBA_STATUS_OK, "case7 FreeLibraryHandler() == HBA_STATUS_OK");

	/* 8. [OHOS] vendor DSO 必须可被 dlopen（libHBAAPI 的加载方式） */
	self = dlopen("libhbalinux.so.2", RTLD_NOW);
	if (self == NULL) {
		printf("     dlopen error: %s\n", dlerror());
	}
	check(self != NULL, "case8 [OHOS] dlopen(\"libhbalinux.so.2\") succeeds");
	if (self != NULL) {
		sym = dlsym(self, "HBA_RegisterLibraryV2");
		check(sym != NULL,
		      "case8b [OHOS] dlopen'd DSO exports HBA_RegisterLibraryV2");
		dlclose(self);
	} else {
		check(0, "case8b [OHOS] dlopen'd DSO exports HBA_RegisterLibraryV2");
	}

	/* 9. [OHOS] 平台事实：无 FC sysfs 树 ⇒ 库不得虚报适配器 */
	if (stat("/sys/class/fc_host", &st) != 0) {
		check(adapters == 0 && epsv2.GetAdapterNameHandler != NULL,
		      "case9 [OHOS] absent fc_host sysfs tree does not fake adapters");
	} else {
		skip("case9 OHOS sysfs fact",
		     "/sys/class/fc_host exists on this host");
	}

	/* 10. v1 注册入口仍然工作（旧版 common library 兼容路径） */
	memset(&epsv1, 0, sizeof(epsv1));
	status = HBA_RegisterLibrary(&epsv1);
	check(status == HBA_STATUS_OK && epsv1.GetNumberOfAdaptersHandler != NULL,
	      "case10 HBA_RegisterLibrary (v1) still registers handlers");

	printf("== result: %d passed, %d failed, %d skipped ==\n",
	       passed, failed, skipped);
	return failed == 0 ? 0 : 1;
}
