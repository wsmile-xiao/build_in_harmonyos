/* libmodi 0-20251121 通用消费者测试（只用已安装包的公开头文件与共享库）。
 *
 * 断言清单（11 项，编号与 test_package/MANIFEST.yml 一致）：
 *  1. libmodi_get_version() 返回上游版本串 "20251121"
 *     （是上游版本，不是本包 Conan 版本 0-20251121）
 *  2. libmodi_get_access_flags_read() == 0x01
 *  3. libmodi_get_access_flags_write() == 0x02
 *  4. libmodi_get_access_flags_read_write() == 0x03
 *  5. libmodi_handle_initialize() == 1
 *  6. libmodi_set_codepage(LIBMODI_CODEPAGE_ASCII) == 1
 *  7. libmodi_get_codepage() 回环读回 == LIBMODI_CODEPAGE_ASCII（20127）
 *  8. libmodi_check_file_signature(NULL, ...) == -1（参数错误路径）
 *  9. libmodi_check_file_signature(不存在路径) == -1（IO 错误路径）
 * 10. libmodi_check_file_signature(100 字节垃圾文件) == 0（无签名）
 * 11. libmodi_handle_open(不存在路径, READ) == -1（打开错误路径）
 * 收尾：close/free 释放句柄（不计断言）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
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
	libmodi_error_t *error = NULL;
	libmodi_handle_t *handle = NULL;
	const char *version = libmodi_get_version();
	const char *missing = "no-such-image-9f3a.bin";

	/* 1. 版本串（上游版本 20251121，非 Conan 版本） */
	CHECK("libmodi_get_version == 20251121",
	      version != NULL && strcmp(version, "20251121") == 0);

	/* 2-4. 访问标志位（definitions.h: READ=0x01 WRITE=0x02） */
	CHECK("access_flags_read == 0x01",
	      libmodi_get_access_flags_read() == 0x01);
	CHECK("access_flags_write == 0x02",
	      libmodi_get_access_flags_write() == 0x02);
	CHECK("access_flags_read_write == 0x03",
	      libmodi_get_access_flags_read_write() == 0x03);

	/* 5. 句柄生命周期起点 */
	CHECK("handle_initialize == 1",
	      libmodi_handle_initialize(&handle, &error) == 1);

	if (handle != NULL) {
		int codepage = 0;

		/* 6-7. codepage 设置与回环（库级设置，ASCII = 20127） */
		CHECK("set_codepage(ASCII) == 1",
		      libmodi_set_codepage(LIBMODI_CODEPAGE_ASCII, &error) == 1);
		CHECK("get_codepage 回环 == 20127",
		      libmodi_get_codepage(&codepage, &error) == 1 &&
		      codepage == LIBMODI_CODEPAGE_ASCII);
	}

	/* 8. 参数错误路径 */
	CHECK("check_file_signature(NULL) == -1",
	      libmodi_check_file_signature(NULL, &error) == -1);

	/* 9. IO 错误路径（文件不存在） */
	CHECK("check_file_signature(missing) == -1",
	      libmodi_check_file_signature(missing, &error) == -1);

	/* 10. 无签名文件（100 字节垃圾内容 → 无 koly 尾块、头签名不匹配） */
	{
		const char *path = "no-signature-garbage.bin";
		FILE *fp = fopen(path, "wb");

		if (fp != NULL) {
			int i;

			for (i = 0; i < 100; i++) {
				fputc(i, fp);
			}
			fclose(fp);

			CHECK("check_file_signature(garbage) == 0",
			      libmodi_check_file_signature(path, &error) == 0);

			remove(path);
		} else {
			CHECK("check_file_signature(garbage) == 0", 0);
		}
	}

	/* 11. 打开错误路径 */
	CHECK("handle_open(missing) == -1",
	      libmodi_handle_open(handle, missing, LIBMODI_OPEN_READ, &error) == -1);

	/* 收尾释放（不计断言） */
	if (handle != NULL) {
		libmodi_handle_close(handle, &error);
		libmodi_handle_free(&handle, &error);
	}

	printf("generic consumer test: %d assertions, %d failed\n",
	       assert_count, fail_count);

	return (fail_count == 0) ? 0 : 1;
}
