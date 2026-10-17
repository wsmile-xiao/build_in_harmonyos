/*
 * composefs 1.0.8 — 消费者用例（业务上层组件模拟，Conan test_package / L1 测试）
 *
 * 仅通过 composefs 已安装/导出的公开头文件（libcomposefs/lcfs-writer.h）、
 * 公开 API（lcfs_node_new / lcfs_node_set_mode / lcfs_node_set_content /
 * lcfs_node_add_child / lcfs_write_to / lcfs_load_node_from_image /
 * lcfs_node_lookup_child / lcfs_node_get_content）与正常链接目标
 * （libcomposefs）使用该三方库，验证第三方使用者能够编译、链接、调用并
 * 正常运行：
 *   1) 在内存中构建一个业务文件树（目录 + app.txt 文本文件）；
 *   2) 通过 lcfs_write_to 生成 EROFS 格式 composefs 镜像文件；
 *   3) 通过 lcfs_load_node_from_image 读回镜像并校验子节点与内容一致；
 *   4) 输出可观察验证结果（镜像字节数、子节点名、内容比对）并退出 0。
 *
 * SPDX-License-Identifier: GPL-2.0-only OR Apache-2.0
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>
#include "libcomposefs/lcfs-writer.h"

static ssize_t file_write_cb(void *_file, void *buf, size_t count)
{
	return fwrite(buf, 1, count, (FILE *)_file);
}

int main(int argc, char **argv)
{
	const char *out = argc > 1 ? argv[1] : "composefs-consumer-out.cfs";
	const char *content = "hello from composefs consumer app\n";
	int rc = 1;

	/* 1. 构建业务文件树 */
	struct lcfs_node_s *root = lcfs_node_new();
	if (root == NULL) {
		fprintf(stderr, "consumer: lcfs_node_new failed: %s\n", strerror(errno));
		goto out;
	}
	lcfs_node_set_mode(root, S_IFDIR | 0755);

	struct lcfs_node_s *app = lcfs_node_new();
	if (app == NULL) {
		fprintf(stderr, "consumer: lcfs_node_new(app) failed: %s\n", strerror(errno));
		goto out;
	}
	lcfs_node_set_mode(app, S_IFREG | 0644);
	if (lcfs_node_set_content(app, (const uint8_t *)content, strlen(content)) != 0) {
		fprintf(stderr, "consumer: lcfs_node_set_content failed\n");
		goto out;
	}
	if (lcfs_node_add_child(root, app, "app.txt") != 0) {
		fprintf(stderr, "consumer: lcfs_node_add_child failed\n");
		goto out;
	}

	/* 2. 生成 EROFS 镜像文件 */
	FILE *f = fopen(out, "we");
	if (f == NULL) {
		fprintf(stderr, "consumer: fopen(%s): %s\n", out, strerror(errno));
		goto out;
	}
	struct lcfs_write_options_s opts = { 0 };
	opts.format = LCFS_FORMAT_EROFS;
	opts.version = 1;
	opts.max_version = LCFS_VERSION_MAX;
	opts.file = f;
	opts.file_write_cb = file_write_cb;
	if (lcfs_write_to(root, &opts) != 0) {
		fprintf(stderr, "consumer: lcfs_write_to: %s\n", strerror(errno));
		fclose(f);
		goto out;
	}
	fflush(f);
	if (fseek(f, 0, SEEK_END) != 0) {
		fprintf(stderr, "consumer: fseek failed\n");
		fclose(f);
		goto out;
	}
	long imgsz = ftell(f);
	fclose(f);
	if (imgsz <= 0) {
		fprintf(stderr, "consumer: empty image (%ld bytes)\n", imgsz);
		goto out;
	}

	/* 3. 读回镜像并校验 */
	FILE *rf = fopen(out, "r");
	if (rf == NULL) {
		fprintf(stderr, "consumer: fopen(%s, r): %s\n", out, strerror(errno));
		goto out;
	}
	uint8_t *imgdata = malloc((size_t)imgsz);
	if (imgdata == NULL || fread(imgdata, 1, (size_t)imgsz, rf) != (size_t)imgsz) {
		fprintf(stderr, "consumer: failed to read image back\n");
		fclose(rf);
		goto out;
	}
	fclose(rf);

	struct lcfs_node_s *root2 = lcfs_load_node_from_image(imgdata, (size_t)imgsz);
	if (root2 == NULL) {
		fprintf(stderr, "consumer: lcfs_load_node_from_image: %s\n", strerror(errno));
		goto out;
	}
	struct lcfs_node_s *app2 = lcfs_node_lookup_child(root2, "app.txt");
	if (app2 == NULL) {
		fprintf(stderr, "consumer: child 'app.txt' not found in image\n");
		goto out;
	}
	const uint8_t *c = lcfs_node_get_content(app2);
	if (c == NULL || memcmp(c, content, strlen(content)) != 0) {
		fprintf(stderr, "consumer: content mismatch after round-trip\n");
		goto out;
	}

	printf("CONSUMER OK: image=%s bytes=%ld child=app.txt content=\"%s\"\n",
	       out, imgsz, content);
	rc = 0;

	lcfs_node_unref(root2);
	lcfs_node_unref(root);
	free(imgdata);
out:
	return rc;
}
