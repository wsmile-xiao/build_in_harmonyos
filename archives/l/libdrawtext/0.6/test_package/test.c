// test_package — 消费者集成测试（R34/R40）：
//
// 【主用例】直接链接消费者可执行程序 —— 上层应用视角验证安装后的包：
//   编译：CC test.c -o consumer -I<package>/include -L<package>/lib -ldrawtext
//   （仅用 Conan 包内 drawtext.h 与 libdrawtext.so，不触碰源码目录）
// 直接调用的公开 API 完整链（非 dlsym 函数指针）：
//   dtx_open_font → dtx_target_raster → dtx_use_font → dtx_prepare_range →
//   dtx_position → dtx_string（ASCII + UTF-8 CJK）→ dtx_string_width/height →
//   dtx_get_font_glyphmap → dtx_get_glyphmap_width/height →
//   dtx_get_glyphmap_image（补丁 0001 补上导出的头文件承诺 API，
//   并验证与 dtx_get_glyphmap_pixels 等价）→ dtx_close_font
// 可观察断言：渲染缓冲非零像素（≥500）、清零重渲染非零、CJK 多字节路径
// 像素、字符串度量 > 0、glyphmap 图集含墨水像素；结束正常释放资源并返回 0。
//
// 【补充用例 -DSYMBOL_PROBE】保留 dlopen + 14 个核心符号 dlsym 解析检查，
// 验证 SONAME 库在运行时可加载且符号视图完整（R40）。
//
// no-opengl 构建（-DNO_OPENGL）下 dtx_target_opengl() 为上游官方 stub，
// 测试显式选择 raster 目标，不依赖任何 GL。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "drawtext.h"	/* Conan 包安装的公开头文件 */

#define W 320
#define H 96

static unsigned char buf[H][W][4];	/* RGBA */

static long nonzero_count(void)
{
	long n = 0;
	for (int j = 0; j < H; j++)
		for (int i = 0; i < W; i++)
			if (buf[j][i][0] || buf[j][i][1] || buf[j][i][2] || buf[j][i][3])
				n++;
	return n;
}

#ifdef SYMBOL_PROBE
#include <dlfcn.h>
/* 补充用例：dlopen SONAME 库并解析 14 个核心符号（链接视图检查）。
   与主用例同一编译单元：直接链接提供 API 声明，此处仅验证动态符号表。 */
static int probe_symbols(const char *so_path)
{
	void *so = dlopen(so_path, RTLD_NOW);
	if (!so) {
		fprintf(stderr, "FAIL: dlopen(%s): %s\n", so_path, dlerror());
		return 1;
	}
	printf("ok: dlopen %s\n", so_path);
	static const char *const syms[] = {
		"dtx_open_font", "dtx_close_font", "dtx_target_raster",
		"dtx_use_font", "dtx_prepare_range", "dtx_position",
		"dtx_string", "dtx_string_width", "dtx_string_height",
		"dtx_get_font_glyphmap", "dtx_get_glyphmap_width",
		"dtx_get_glyphmap_height", "dtx_get_glyphmap_pixels",
		"dtx_get_glyphmap_image",
	};
	int bad = 0;
	int total = (int)(sizeof(syms) / sizeof(syms[0]));
	for (size_t i = 0; i < sizeof(syms) / sizeof(syms[0]); i++) {
		if (!dlsym(so, syms[i])) {
			fprintf(stderr, "FAIL: dlsym(%s): %s\n", syms[i], dlerror());
			bad++;
		}
	}
	dlclose(so);
	if (bad)
		return 1;
	printf("ok: all %d symbols resolved\n", total);
	return 0;
}
#endif

int main(int argc, char **argv)
{
	int failures = 0;

#ifdef SYMBOL_PROBE
	/* 补充用例：仅做 dlopen + 14 符号解析，随后退出（不重复渲染链，
	   也不链接 -ldrawtext —— 只验证运行时动态符号视图） */
	if (argc < 2) {
		fprintf(stderr, "usage: %s <libdrawtext.so>\n", argv[0]);
		return 1;
	}
	if (probe_symbols(argv[1]))
		return 1;
	puts("ALL TESTS PASSED");
	return 0;
#else
	(void)argc; (void)argv;
#endif

	/* 字体回退链：本机系统字体目录，覆盖 ASCII + CJK（U+4E2D） */
	const char *fallbacks[] = {
		"/system/fonts/HarmonyOS_Sans_SC.ttf",
		"/system/fonts/HarmonyOS_Sans.ttf",
		"/system/fonts/FZHeiT-SC-Regular.ttf",
		NULL,
	};
	const char *font = NULL;
	for (int i = 0; fallbacks[i]; i++) {
		FILE *fp = fopen(fallbacks[i], "rb");
		if (fp) {
			fclose(fp);
			font = fallbacks[i];
			break;
		}
	}
	if (!font) {
		fprintf(stderr, "FAIL: no usable system font found\n");
		return 1;
	}
	printf("using font: %s\n", font);

	memset(buf, 0, sizeof(buf));
	struct dtx_font *fnt = dtx_open_font(font, 32);
	if (!fnt) {
		fprintf(stderr, "FAIL: dtx_open_font(%s) returned NULL\n", font);
		return 1;
	}

	/* 软件光栅化目标（无需 GL），先于 dtx_use_font 设置 */
	dtx_target_raster(&buf[0][0][0], W, H);
	dtx_use_font(fnt, 32);
	dtx_prepare_range(fnt, 32, 32, 126);		/* ASCII 可见字符 */
	dtx_prepare_range(fnt, 32, 0x4e2d, 0x4e2d);	/* CJK 表意文字 */
	dtx_position(8, 48);
	dtx_string("libdrawtext");
	dtx_position(8, 88);
	dtx_string("\xe4\xb8\xad");	/* U+4E2D UTF-8（utf8.c 多字节路径） */

	/* 断言 1：像素真实写入 */
	long px = nonzero_count();
	if (px < 500) {
		fprintf(stderr, "FAIL: rendered nonzero pixels = %ld (expected >= 500)\n", px);
		failures++;
	} else {
		printf("ok: rendered %ld nonzero pixels\n", px);
	}

	/* 断言 2：清零重渲染（排除残留可能） */
	memset(buf, 0, sizeof(buf));
	if (nonzero_count() != 0) {
		fprintf(stderr, "FAIL: buffer not clear\n");
		failures++;
	}
	dtx_position(8, 48);
	dtx_string("libdrawtext");
	if (nonzero_count() < 400) {
		fprintf(stderr, "FAIL: re-render produced too few pixels\n");
		failures++;
	} else {
		printf("ok: re-render after clear\n");
	}

	/* 断言 3：度量 API（宽高 > 0，量级合理） */
	float mw = dtx_string_width("libdrawtext");
	float mh = dtx_string_height("libdrawtext");
	if (mw <= 0.0f || mh <= 0.0f || mh > 100.0f) {
		fprintf(stderr, "FAIL: dtx_string_width/height = %f/%f\n", mw, mh);
		failures++;
	} else {
		printf("ok: string metrics %.1fx%.1f\n", mw, mh);
	}

	/* 断言 4：glyphmap 图集非空 —— 直接调用公共头文件声明的
	   dtx_get_glyphmap_image（drawtext.h 自 0.6 起承诺但实现遗漏，
	   补丁 0001 以别名形式补上导出），内存遍历像素；同时调用补齐
	   声明的 dtx_get_glyphmap_pixels 验证二者返回同一数据（真别名）。 */
	struct dtx_glyphmap *gmap = dtx_get_font_glyphmap(fnt, 32, 'A');
	if (!gmap) {
		fprintf(stderr, "FAIL: dtx_get_font_glyphmap('A') = NULL\n");
		failures++;
	} else {
		int gw = dtx_get_glyphmap_width(gmap);
		int gh = dtx_get_glyphmap_height(gmap);
		unsigned char *img = dtx_get_glyphmap_image(gmap);
		unsigned char *pix = dtx_get_glyphmap_pixels(gmap);
		long ink = 0;
		if (gw <= 0 || gh <= 0 || !img || !pix) {
			fprintf(stderr, "FAIL: glyphmap %dx%d img=%p pix=%p\n",
				gw, gh, (void *)img, (void *)pix);
			failures++;
		} else if (img != pix) {
			fprintf(stderr, "FAIL: dtx_get_glyphmap_image != dtx_get_glyphmap_pixels\n");
			failures++;
		} else {
			for (long i = 0; i < (long)gw * gh; i++)
				if (img[i])
					ink++;
			if (ink < 50) {
				fprintf(stderr, "FAIL: glyphmap atlas ink = %ld (too few)\n", ink);
				failures++;
			} else {
				printf("ok: glyphmap %dx%d, %ld ink pixels (image==pixels)\n",
					gw, gh, ink);
			}
		}
	}

	dtx_close_font(fnt);	/* 正常释放资源 */

	if (failures) {
		fprintf(stderr, "TEST FAILED: %d assertion(s)\n", failures);
		return 1;
	}
	puts("ALL TESTS PASSED");
	return 0;
}
