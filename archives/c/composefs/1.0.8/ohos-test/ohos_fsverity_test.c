/*
 * composefs 1.0.8 — HarmonyOS PC (aarch64) 专项测试
 *
 * 覆盖点（均对应本轮 OHOS 适配补丁的实际行为）：
 *  A. lcfs_fd_measure_fsverity 在 HMFS 上返回 -ENOVERITY：
 *     HarmonyOS 文件系统对 FS_IOC_MEASURE_VERITY 返回 EACCES/EINVAL
 *     （Linux 为 ENODATA/ENOTTY/EOPNOTSUPP），本库补丁将其归一化为 ENOVERITY，
 *     避免构建因 ioctl 语义差异而中止。
 *  B. lcfs_fd_get_fsverity 在无 fs-verity 支持的文件系统上回退为进程内计算，
 *     且结果确定（同内容同摘要、异内容异摘要）。
 *  C. 公共 API 内存往返：节点树(lcfs_node_new/set_mode/set_content/add_child)
 *     -> lcfs_write_to 生成 EROFS 镜像 -> lcfs_load_node_from_image 读回
 *     -> 校验子节点内容一致。
 *
 * SPDX-License-Identifier: GPL-2.0-only OR Apache-2.0
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/stat.h>
#include "libcomposefs/lcfs-writer.h"
#include "libcomposefs/lcfs-mount.h" /* ENOVERITY / EWRONGVERITY */

#define PASS(fmt, ...) do { printf("[PASS] " fmt "\n", ##__VA_ARGS__); } while (0)
#define FAIL(fmt, ...) do { printf("[FAIL] " fmt "\n", ##__VA_ARGS__); exit(1); } while (0)

static void print_digest(const uint8_t *d)
{
	for (int i = 0; i < LCFS_DIGEST_SIZE; i++)
		printf("%02x", d[i]);
	printf("\n");
}

static ssize_t file_write_cb(void *_file, void *buf, size_t count)
{
	return fwrite(buf, 1, count, (FILE *)_file);
}

int main(int argc, char **argv)
{
	const char *tmpdir = getenv("TMPDIR");
	char tmpname[512];

	if (tmpdir == NULL)
		tmpdir = "/tmp";
	snprintf(tmpname, sizeof(tmpname), "%s/ohos-fsverity.XXXXXX", tmpdir);

	/* ── A. measure 归一化 ── */
	int fd = mkstemp(tmpname);
	if (fd < 0)
		FAIL("mkstemp(%s): %s", tmpname, strerror(errno));
	if (write(fd, "composefs ohos test data", 24) != 24)
		FAIL("write: %s", strerror(errno));

	uint8_t digest[LCFS_DIGEST_SIZE];
	errno = 0;
	int r = lcfs_fd_measure_fsverity(digest, fd);
	if (r == -ENOVERITY)
		PASS("A) measure returns -ENOVERITY (r=%d, HMFS ioctl EACCES canonicalized)", r);
	else
		FAIL("A) measure r=%d (expected -%d ENOVERITY), errno=%d", r, ENOVERITY, errno);

	/* ── B. 进程内 fs-verity 计算：确定性 + 内容敏感性 ── */
	uint8_t d1[LCFS_DIGEST_SIZE], d2[LCFS_DIGEST_SIZE], d3[LCFS_DIGEST_SIZE];
	if (lcfs_fd_get_fsverity(d1, fd) != 0)
		FAIL("B) get_fsverity#1: %s", strerror(errno));
	if (lseek(fd, 0, SEEK_SET) < 0 || lcfs_fd_get_fsverity(d2, fd) != 0)
		FAIL("B) get_fsverity#2: %s", strerror(errno));
	if (memcmp(d1, d2, LCFS_DIGEST_SIZE) != 0)
		FAIL("B) digest not deterministic across calls");
	PASS("B) in-memory fsverity digest deterministic: ");
	print_digest(d1);

	if (write(fd, "X", 1) != 1)
		FAIL("write#2: %s", strerror(errno));
	if (lseek(fd, 0, SEEK_SET) < 0 || lcfs_fd_get_fsverity(d3, fd) != 0)
		FAIL("B) get_fsverity#3: %s", strerror(errno));
	if (memcmp(d1, d3, LCFS_DIGEST_SIZE) == 0)
		FAIL("B) digest NOT content-sensitive");
	PASS("B) digest content-sensitive (changed after content change)");
	close(fd);
	unlink(tmpname);

	/* ── C. 公共 API 内存往返 ── */
	struct lcfs_node_s *root = lcfs_node_new();
	if (root == NULL)
		FAIL("C) node_new");
	lcfs_node_set_mode(root, S_IFDIR | 0755);
	struct lcfs_node_s *app = lcfs_node_new();
	if (app == NULL)
		FAIL("C) node_new child");
	lcfs_node_set_mode(app, S_IFREG | 0644);
	const char content[] = "ohos round-trip content";
	if (lcfs_node_set_content(app, (const uint8_t *)content,
				  sizeof(content) - 1) != 0)
		FAIL("C) set_content");
	if (lcfs_node_add_child(root, app, "app.txt") != 0)
		FAIL("C) add_child");

	/* write to real temp file (open_memstream is unreliable on this toolchain) */
	snprintf(tmpname, sizeof(tmpname), "%s/ohos-rt.XXXXXX", tmpdir);
	int imfd = mkstemp(tmpname);
	if (imfd < 0)
		FAIL("C) mkstemp image: %s", strerror(errno));
	FILE *f = fdopen(imfd, "w+");
	if (f == NULL)
		FAIL("C) fdopen: %s", strerror(errno));

	struct lcfs_write_options_s opts = { 0 };
	opts.format = LCFS_FORMAT_EROFS;
	opts.version = 1;
	opts.max_version = LCFS_VERSION_MAX;
	opts.file = f;
	opts.file_write_cb = file_write_cb;
	if (lcfs_write_to(root, &opts) != 0)
		FAIL("C) lcfs_write_to: %s", strerror(errno));
	fflush(f);
	rewind(f);
	if (fseek(f, 0, SEEK_END) != 0)
		FAIL("C) seek end");
	long imgsz = ftell(f);
	if (imgsz <= 0)
		FAIL("C) empty image (%ld bytes)", imgsz);
	rewind(f);
	uint8_t *imgdata = malloc((size_t)imgsz);
	if (imgdata == NULL || fread(imgdata, 1, (size_t)imgsz, f) != (size_t)imgsz)
		FAIL("C) read image");
	fclose(f);

	struct lcfs_node_s *root2 = lcfs_load_node_from_image(imgdata, (size_t)imgsz);
	if (root2 == NULL)
		FAIL("C) load_node_from_image: %s", strerror(errno));
	struct lcfs_node_s *app2 = lcfs_node_lookup_child(root2, "app.txt");
	if (app2 == NULL)
		FAIL("C) child 'app.txt' not found in image");
	const uint8_t *c = lcfs_node_get_content(app2);
	if (c == NULL || memcmp(c, content, sizeof(content) - 1) != 0)
		FAIL("C) content mismatch after round-trip");
	PASS("C) public-API EROFS round-trip OK (image %ld bytes, content verified)",
	     imgsz);

	unlink(tmpname);
	free(imgdata);
	lcfs_node_unref(root);
	lcfs_node_unref(root2);
	PASS("ohos_fsverity_test: ALL PASS");
	return 0;
}