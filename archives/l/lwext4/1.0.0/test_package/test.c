/*
 * test_package consumer test — lwext4 1.0.0
 *
 * R34: 必须实质调用被测包 API。本测试实现一个内存 RAM 块设备
 * (EXT4_BLOCKDEV_STATIC_INSTANCE)，走完整 ext4 流程：
 * mkfs → mount → fopen/fwrite/fread/fclose → umount。
 */
#include <ext4.h>
#include <ext4_mkfs.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#define RAM_BSIZE 4096
#define RAM_BCNT  16384  /* 64 MiB */

static uint8_t rambuf[RAM_BSIZE * RAM_BCNT];

static int ram_open(struct ext4_blockdev *bd) { (void)bd; return EOK; }
static int ram_close(struct ext4_blockdev *bd) { (void)bd; return EOK; }
static int ram_lock(struct ext4_blockdev *bd) { (void)bd; return EOK; }
static int ram_unlock(struct ext4_blockdev *bd) { (void)bd; return EOK; }

static int ram_bread(struct ext4_blockdev *bd, void *buf, uint64_t blk_id,
                     uint32_t blk_cnt)
{
    (void)bd;
    if (blk_id + blk_cnt > RAM_BCNT)
        return ENOTSUP;
    memcpy(buf, rambuf + (size_t)blk_id * RAM_BSIZE, (size_t)blk_cnt * RAM_BSIZE);
    return EOK;
}

static int ram_bwrite(struct ext4_blockdev *bd, const void *buf,
                      uint64_t blk_id, uint32_t blk_cnt)
{
    (void)bd;
    if (blk_id + blk_cnt > RAM_BCNT)
        return ENOTSUP;
    memcpy(rambuf + (size_t)blk_id * RAM_BSIZE, buf, (size_t)blk_cnt * RAM_BSIZE);
    return EOK;
}

EXT4_BLOCKDEV_STATIC_INSTANCE(ram_bd, RAM_BSIZE, RAM_BCNT, ram_open, ram_bread,
                              ram_bwrite, ram_close, ram_lock, ram_unlock);

int main(void)
{
    struct ext4_fs fs;
    struct ext4_bcache bc;
    struct ext4_mkfs_info mkfs = {0};
    ext4_file f;
    const char *payload = "lwext4-harmonyos-consumer-test";
    char readback[64] = {0};
    size_t wcnt = 0, rcnt = 0;
    int rc;

    memset(&fs, 0, sizeof(fs));
    memset(&bc, 0, sizeof(bc));

    rc = ext4_bcache_init_dynamic(&bc, 16, RAM_BSIZE);
    if (rc != EOK) {
        printf("ext4_bcache_init_dynamic FAILED rc=%d\n", rc);
        return 1;
    }

    rc = ext4_device_register(&ram_bd, &bc, "ramdisk");
    if (rc != EOK) {
        printf("ext4_device_register FAILED rc=%d\n", rc);
        return 1;
    }

    mkfs.block_size = RAM_BSIZE;
    mkfs.journal = 0;
    mkfs.label = "lwext4-test";
    rc = ext4_mkfs(&fs, &ram_bd, &mkfs, F_SET_EXT4);
    if (rc != EOK) {
        printf("ext4_mkfs FAILED rc=%d\n", rc);
        return 1;
    }

    rc = ext4_mount("ramdisk", "/", false);
    if (rc != EOK) {
        printf("ext4_mount FAILED rc=%d\n", rc);
        return 1;
    }

    rc = ext4_fopen(&f, "/hello.txt", "wb");
    if (rc != EOK) {
        printf("ext4_fopen(w) FAILED rc=%d\n", rc);
        return 1;
    }
    rc = ext4_fwrite(&f, payload, strlen(payload), &wcnt);
    if (rc != EOK || wcnt != strlen(payload)) {
        printf("ext4_fwrite FAILED rc=%d wcnt=%zu\n", rc, wcnt);
        return 1;
    }
    ext4_fclose(&f);

    rc = ext4_fopen(&f, "/hello.txt", "rb");
    if (rc != EOK) {
        printf("ext4_fopen(r) FAILED rc=%d\n", rc);
        return 1;
    }
    rc = ext4_fread(&f, readback, sizeof(readback) - 1, &rcnt);
    if (rc != EOK || rcnt != strlen(payload) ||
        memcmp(readback, payload, rcnt) != 0) {
        printf("ext4_fread FAILED rc=%d rcnt=%zu\n", rc, rcnt);
        return 1;
    }
    ext4_fclose(&f);

    rc = ext4_umount("/");
    if (rc != EOK) {
        printf("ext4_umount FAILED rc=%d\n", rc);
        return 1;
    }

    printf("lwext4 consumer test PASSED: mkfs+mount+write+read+umount ok\n");
    return 0;
}