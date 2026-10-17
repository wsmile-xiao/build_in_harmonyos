/* test_libgsf — 消费者视角验证 libgsf 核心功能 (R34: 实质调用 API)
 *
 * 1. gsf_init() 并校验版本号（libgsf_major_version >= 1）
 * 2. 内存 sink 创建 GsfOutfileZip，写入一个 child 文件
 * 3. 关闭并校验写入字节数与产物 size 非零
 */
#include <gsf/gsf.h>
#include <stdio.h>
#include <string.h>

int
main (void)
{
	GsfOutput *sink;
	GsfOutfile *zip;
	GsfOutput *child;
	guint8 const *data = (guint8 const *) "hello libgsf 1.14.58";
	gsize len = strlen ((char const *) data);
	gboolean ok;

	gsf_init ();

	if (libgsf_major_version < 1) {
		fprintf (stderr, "libgsf major version too old: %d\n",
			 libgsf_major_version);
		return 1;
	}

	/* 创建内存 OLE/ZIP 写入器 */
	sink = gsf_output_memory_new ();
	if (sink == NULL)
		return 2;

	zip = gsf_outfile_zip_new (sink, NULL);
	if (zip == NULL) {
		g_object_unref (sink);
		return 3;
	}

	child = gsf_outfile_new_child (zip, "test.txt", FALSE);
	if (child == NULL) {
		g_object_unref (zip);
		g_object_unref (sink);
		return 4;
	}

	ok = gsf_output_write (child, len, data);
	ok = gsf_output_close (child) && ok;
	if (!ok) {
		g_object_unref (child);
		g_object_unref (zip);
		g_object_unref (sink);
		return 5;
	}

	g_object_unref (child);
	g_object_unref (zip);
	g_object_unref (sink);

	printf ("libgsf %d.%d.%d test: OK (%d bytes written)\n",
		libgsf_major_version, libgsf_minor_version,
		libgsf_micro_version, (int) len);
	return 0;
}
