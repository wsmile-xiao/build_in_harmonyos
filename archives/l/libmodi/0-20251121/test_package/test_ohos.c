/* libmodi 0-20251121 鸿蒙专项消费者测试（OHOS 专属，settings.os=OHOS 才编译运行）。
 *
 * 断言清单（11 项，编号与 test_package/MANIFEST.yml 一致）：
 *  1. __OHOS__ 编译目标生效
 *  2. TMPDIR 已设置且不是只读的 /tmp
 *  3. TMPDIR 指向的目录真实存在
 *  4. TMPDIR 可写（探针文件创建+删除）
 *  5. 在 TMPDIR 下合成 512 字节 UDIF koly 尾块文件（魔数 "koly"）
 *  6. libmodi_check_file_signature(koly 文件) == 1（真实签名判定读回）
 *  7. libmodi_handle_initialize() == 1
 *  8. libmodi_handle_open(koly 文件, LIBMODI_OPEN_READ) == 1
 *     （UDIF 打开对 koly 尾块惰性解析——实测返回成功）
 *  9. libmodi_handle_get_media_size() == 1 且 size == 0（合成尾块字段全零）
 * 10. libmodi_handle_close() == 0
 * 11. libmodi_handle_free() == 1
 * 收尾：删除合成文件（不计断言）。
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <libmodi.h>

#define CHECK(msg, cond)						\
	do {								\
		if (cond) {						\
			printf("PASS %d: %s\n", ++assert_count, msg);	\
		} else {						\
			printf("FAIL %d: %s\n", ++assert_count, msg);	\
			fail_count++;					\
		}							\
	} while (0)

int main(void)
{
	int assert_count = 0;
	int fail_count   = 0;
	const char *tmpdir = getenv("TMPDIR");
	char koly_path[1024];
	FILE *fp = NULL;
	libmodi_error_t *error = NULL;
	libmodi_handle_t *handle = NULL;

	/* 1. __OHOS__ 编译目标 */
#ifdef __OHOS__
	CHECK("__OHOS__ defined", 1);
#else
	CHECK("__OHOS__ defined", 0);
#endif

	/* 2-4. TMPDIR 语义（鸿蒙设备 /tmp 只读，依赖方必须给出可写临时目录） */
	CHECK("TMPDIR set and != /tmp",
	      tmpdir != NULL && strcmp(tmpdir, "/tmp") != 0);

	if (tmpdir != NULL) {
		struct stat st;

		CHECK("TMPDIR directory exists",
		      stat(tmpdir, &st) == 0 && S_ISDIR(st.st_mode));
	} else {
		CHECK("TMPDIR directory exists", 0);
	}

	if (tmpdir != NULL) {
		char probe[1024];

		snprintf(probe, sizeof(probe), "%s/libmodi-ohos-probe.tmp",
			 tmpdir);
		fp = fopen(probe, "wb");

		if (fp != NULL) {
			fclose(fp);
			CHECK("TMPDIR writable", remove(probe) == 0);
		} else {
			CHECK("TMPDIR writable", 0);
		}

		snprintf(koly_path, sizeof(koly_path), "%s/libmodi-koly.bin",
			 tmpdir);

		/* 5. 合成 512 字节 UDIF koly 尾块（魔数 + 全零字段） */
		fp = fopen(koly_path, "wb");

		if (fp != NULL) {
			unsigned char trailer[512];

			memset(trailer, 0, sizeof(trailer));
			memcpy(trailer, "koly", 4);
			CHECK("koly trailer written == 512B",
			      fwrite(trailer, 1, sizeof(trailer), fp) ==
			      sizeof(trailer) && fclose(fp) == 0);
		} else {
			CHECK("koly trailer written == 512B", 0);
		}
	} else {
		CHECK("TMPDIR writable", 0);
		CHECK("koly trailer written == 512B", 0);
	}

	/* 6. 签名判定真实读回：koly 尾块命中 */
	CHECK("check_file_signature(koly) == 1",
	      libmodi_check_file_signature(koly_path, &error) == 1);

	/* 7-11. 打开 → 读 media size → 关闭 → 释放 完整链路 */
	CHECK("handle_initialize == 1",
	      libmodi_handle_initialize(&handle, &error) == 1);

	if (handle != NULL) {
		size64_t media_size = 0;
		int ro = libmodi_handle_open(handle, koly_path,
					     LIBMODI_OPEN_READ, &error);

		CHECK("handle_open(koly) == 1", ro == 1);

		if (ro == 1) {
			CHECK("get_media_size == 1 && size == 0",
			      libmodi_handle_get_media_size(
				      handle, &media_size, &error) == 1 &&
			      media_size == 0);
		} else {
			CHECK("get_media_size == 1 && size == 0", 0);
		}

		CHECK("handle_close == 0", libmodi_handle_close(handle, &error) == 0);
	}
	CHECK("handle_free == 1", libmodi_handle_free(&handle, &error) == 1);

	/* 收尾：删除合成文件（不计断言） */
	remove(koly_path);

	printf("ohos specific test: %d assertions, %d failed\n",
	       assert_count, fail_count);

	return (fail_count == 0) ? 0 : 1;
}
