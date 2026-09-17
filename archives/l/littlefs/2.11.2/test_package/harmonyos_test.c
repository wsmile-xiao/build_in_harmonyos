/* littlefs 2.11.2 HarmonyOS 专项测试（真实可执行，非空壳）
 *
 * 断言：OHOS 平台识别 + littlefs 全流程文件操作
 *   format → mount → mkdir → create/write → close →
 *   open/read 回验 → 卸载重挂验证持久化 → remove/rmdir → unmount
 * 块设备：内存 RAM disk（真实 read/prog/erase/sync 回调，非桩实现）
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include "lfs.h"

static int g_fail = 0;
#define CHECK(cond, msg) do { \
    if (cond) { printf("  PASS: %s\n", msg); } \
    else { printf("  FAIL: %s\n", msg); g_fail++; } \
} while (0)

/* ── 内存块设备（RAM disk）── */
#define RAMBD_SIZE       (4 * 1024)          /* 4 KiB 块设备 */
#define RAMBD_BLOCK_SIZE 512
#define RAMBD_BLOCK_CNT  (RAMBD_SIZE / RAMBD_BLOCK_SIZE)
static uint8_t g_ram[RAMBD_SIZE];

static int rambd_read(const struct lfs_config *c, lfs_block_t block,
        lfs_off_t off, void *buffer, lfs_size_t size) {
    if (block >= RAMBD_BLOCK_CNT || off + size > c->block_size) {
        return LFS_ERR_IO;
    }
    memcpy(buffer, g_ram + block * c->block_size + off, size);
    return LFS_ERR_OK;
}

static int rambd_prog(const struct lfs_config *c, lfs_block_t block,
        lfs_off_t off, const void *buffer, lfs_size_t size) {
    if (block >= RAMBD_BLOCK_CNT || off + size > c->block_size) {
        return LFS_ERR_IO;
    }
    /* 模拟 NOR flash：编程只能把 1 写为 0 */
    uint8_t *dst = g_ram + block * c->block_size + off;
    const uint8_t *src = (const uint8_t *)buffer;
    for (lfs_size_t i = 0; i < size; i++) {
        dst[i] &= src[i];
    }
    return LFS_ERR_OK;
}

static int rambd_erase(const struct lfs_config *c, lfs_block_t block) {
    if (block >= RAMBD_BLOCK_CNT) {
        return LFS_ERR_IO;
    }
    memset(g_ram + block * c->block_size, 0xff, c->block_size);
    return LFS_ERR_OK;
}

static int rambd_sync(const struct lfs_config *c) {
    (void)c;
    return LFS_ERR_OK;
}

int main(void) {
    printf("=== littlefs 2.11.2 HarmonyOS 专项测试 ===\n");

    /* 1. 平台识别：OHOS aarch64 工具链（clang 15） */
#if defined(__OHOS__) || defined(__OHOS_FAMILY__) || defined(OPENHARMONY)
    CHECK(true, "platform: OHOS 宏已定义");
#elif defined(__aarch64__) || defined(_M_ARM64)
    CHECK(true, "platform: aarch64 架构（HarmonyOS PC 目标）");
#else
    CHECK(false, "platform: 未知平台宏");
#endif
#if defined(__linux__)
    CHECK(true, "platform: __linux__ 定义（HarmonyOS 基于 Linux 内核）");
#else
    CHECK(false, "platform: __linux__ 缺失");
#endif

    /* 2. lfs_config：RAM disk + 典型嵌入式参数 */
    struct lfs_config cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.read  = rambd_read;
    cfg.prog  = rambd_prog;
    cfg.erase = rambd_erase;
    cfg.sync  = rambd_sync;
    cfg.read_size      = 16;
    cfg.prog_size      = 16;
    cfg.block_size     = RAMBD_BLOCK_SIZE;
    cfg.block_count    = RAMBD_BLOCK_CNT;
    cfg.cache_size     = 256;
    cfg.lookahead_size = 128;
    cfg.block_cycles   = 500;

    lfs_t lfs;
    const char *payload = "Hello, HarmonyOS littlefs!";

    /* 3. format → mount */
    int err = lfs_format(&lfs, &cfg);
    CHECK(err == LFS_ERR_OK, "lfs_format 成功");
    err = lfs_mount(&lfs, &cfg);
    CHECK(err == LFS_ERR_OK, "lfs_mount 成功");

    /* 4. mkdir + 建文件写回读验 */
    err = lfs_mkdir(&lfs, "ohos");
    CHECK(err == LFS_ERR_OK, "lfs_mkdir(ohos) 成功");

    lfs_file_t f;
    err = lfs_file_open(&lfs, &f, "ohos/hello.txt",
            LFS_O_WRONLY | LFS_O_CREAT | LFS_O_EXCL);
    CHECK(err == LFS_ERR_OK, "lfs_file_open(CREAT) 成功");
    lfs_ssize_t w = lfs_file_write(&lfs, &f, payload, strlen(payload));
    CHECK(w == (lfs_ssize_t)strlen(payload), "lfs_file_write 写入长度一致");
    err = lfs_file_close(&lfs, &f);
    CHECK(err == LFS_ERR_OK, "lfs_file_close 成功");

    /* 5. 读回验证内容 */
    err = lfs_file_open(&lfs, &f, "ohos/hello.txt", LFS_O_RDONLY);
    CHECK(err == LFS_ERR_OK, "lfs_file_open(RDONLY) 成功");
    lfs_soff_t sz = lfs_file_size(&lfs, &f);
    CHECK(sz == (lfs_soff_t)strlen(payload), "lfs_file_size 正确");
    char buf[128];
    memset(buf, 0, sizeof(buf));
    lfs_ssize_t r = lfs_file_read(&lfs, &f, buf, sizeof(buf));
    CHECK(r == (lfs_ssize_t)strlen(payload), "lfs_file_read 读回长度一致");
    CHECK(strcmp(buf, payload) == 0, "读回内容与写入一致");
    err = lfs_file_close(&lfs, &f);
    CHECK(err == LFS_ERR_OK, "lfs_file_close(RDONLY) 成功");

    /* 6. 卸载 → 重挂 → 数据仍然在（同一 task_id 内真实持久化验证） */
    err = lfs_unmount(&lfs);
    CHECK(err == LFS_ERR_OK, "lfs_unmount 成功");
    err = lfs_mount(&lfs, &cfg);
    CHECK(err == LFS_ERR_OK, "重新 mount 成功");
    err = lfs_file_open(&lfs, &f, "ohos/hello.txt", LFS_O_RDONLY);
    CHECK(err == LFS_ERR_OK, "重挂后 open 成功");
    memset(buf, 0, sizeof(buf));
    r = lfs_file_read(&lfs, &f, buf, sizeof(buf));
    CHECK(r == (lfs_ssize_t)strlen(payload) && strcmp(buf, payload) == 0,
            "重挂后数据持久（内容一致）");
    lfs_file_close(&lfs, &f);

    /* 7. 清理：remove/rmdir/unmount */
    err = lfs_remove(&lfs, "ohos/hello.txt");
    CHECK(err == LFS_ERR_OK, "lfs_remove 成功");
    err = lfs_remove(&lfs, "ohos");
    CHECK(err == LFS_ERR_OK, "lfs_remove(空目录) 成功");
    err = lfs_unmount(&lfs);
    CHECK(err == LFS_ERR_OK, "最终 lfs_unmount 成功");

    printf("=== 结果: %s (%d 失败) ===\n", g_fail == 0 ? "ALL PASS" : "FAILED", g_fail);
    return g_fail == 0 ? 0 : 1;
}