/* test_libexif_gtk.c — libexif-gtk 0.5.0 消费者测试（conan test_package）
 *
 * 6 条断言，其中 1 条为鸿蒙特有用例（OHOS-1）。
 * 全部用例都不需要显示后端：只走 GType 注册 / dlopen 符号解析 /
 * libexif 数据模型构造路径（GTK 控件实例化需要显示，故不在此处做）。
 *
 *  1. gtk_exif_browser_get_type()      —— 被测包真实 API（GtkExifBrowser GType）
 *  2. gtk_exif_content_list_get_type() —— 被测包真实 API（GtkExifContentList GType）
 *  3. dlopen(RTLD_NOW)                 —— .so 全部符号可解析（非 NLS 分支
 *                                         bind_textdomain_codeset 修补的直接证据）
 *  4. dlsym("gtk_exif_browser_new")    —— 公共构造入口已导出
 *  5. exif_data_new()                  —— 传递依赖 libexif 运行期可用
 *  6. uname() == HarmonyOS             —— 鸿蒙特有用例（OHOS-1）
 */
#include <libexif-gtk/gtk-exif-browser.h>
#include <libexif-gtk/gtk-exif-content-list.h>
#include <libexif/exif-data.h>

#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>

static int g_checks = 0;
static int g_failed = 0;

static void check(int cond, const char *what)
{
	g_checks++;
	if (cond) {
		printf("PASS [%d]: %s\n", g_checks, what);
	} else {
		g_failed++;
		printf("FAIL [%d]: %s\n", g_checks, what);
	}
}

int main(void)
{
	GType browser_type;
	GType list_type;
	void *handle;
	ExifData *data;
	struct utsname u;

	/* 1. 被测包真实 API：类型注册（无需显示环境） */
	browser_type = gtk_exif_browser_get_type();
	check(browser_type != 0,
	      "gtk_exif_browser_get_type() registers a GType");

	/* 2. 被测包真实 API：第二个导出类型 */
	list_type = gtk_exif_content_list_get_type();
	check(list_type != 0,
	      "gtk_exif_content_list_get_type() registers a GType");

	/* 3. 共享库符号完整性：RTLD_NOW 强制解析全部未定义符号。
	 *    OHOS 无 libc libintl，若非 NLS 分支缺 bind_textdomain_codeset 桩，
	 *    此处会以 "symbol not found" 失败（本地首个链接错误根因）。 */
	handle = dlopen("libexif-gtk3.so.5", RTLD_NOW | RTLD_GLOBAL);
	check(handle != NULL,
	      "dlopen(libexif-gtk3.so.5, RTLD_NOW) resolves every symbol");
	if (handle != NULL) {
		check(dlsym(handle, "gtk_exif_browser_new") != NULL,
		      "gtk_exif_browser_new symbol is exported");
	} else {
		check(0, "gtk_exif_browser_new symbol is exported (dlopen failed)");
	}

	/* 4. 传递依赖 libexif 运行期可用（EXIF 数据模型构造/释放） */
	data = exif_data_new();
	check(data != NULL, "exif_data_new() works (libexif transitive dep)");
	if (data != NULL) {
		exif_data_free(data);
	}

	/* 5. 鸿蒙特有用例 OHOS-1：确认运行平台为 HarmonyOS */
	memset(&u, 0, sizeof(u));
	check(uname(&u) == 0 && strstr(u.sysname, "HarmonyOS") != NULL,
	      "OHOS-1: uname() reports HarmonyOS");

	printf("\nlibexif-gtk 0.5.0 test_package: %d checks, %d failed\n",
	       g_checks, g_failed);
	return g_failed == 0 ? 0 : 1;
}
