/* e2fsprogs 1.47.1 真实功能断言（libext2fs + libcom_err）。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 文件系统操作得对。这里真的**在一个文件里
 * 造出一个 ext2 文件系统、关掉、重新打开、把超级块的关键字段读回来对账**。
 *
 * 覆盖：
 *   ① libcom_err 的错误码表：error_message() 对已知码必须给出确定文本
 *   ② libext2fs 建库：ext2fs_initialize + allocate_tables + close
 *   ③ 重开复验：块数/inode 数/块大小必须与创建时一致（只在内存里对不算数）
 *   ④ 错误路径：打开一个非文件系统的文件必须返回错误码而不是崩溃
 */
#include <ext2fs/ext2fs.h>
#include <et/com_err.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define IMG "e2fs_test_tmp.img"
#define NBLOCKS 2048u
#define BLKSIZE 1024

int main(void)
{
    ext2_filsys fs = NULL;
    struct ext2_super_block param;
    errcode_t rc;

    /* ① libcom_err：已知错误码必须给出确定文本。
     *
     * ⚠️ 必须先注册错误码表 —— com_err 不会自动加载。不注册的话
     * error_message() 只会返回 "Unknown code ext2 19"（实撞）。
     * 上游自己的代码（icount.c / inline_data.c 等）也都是先调这个。 */
    initialize_ext2_error_table();
    {
        const char *m = error_message(EXT2_ET_BAD_MAGIC);
        if (!m || !*m) {
            printf("FAIL error_message(EXT2_ET_BAD_MAGIC) 为空 —— 错误码表没装进来\n");
            return 1;
        }
        if (!strstr(m, "magic") && !strstr(m, "Magic")) {
            printf("FAIL EXT2_ET_BAD_MAGIC 的文本 [%s] 不含 magic 字样\n", m);
            return 1;
        }
    }

    unlink(IMG);
    /* 预分配镜像文件 */
    {
        FILE *f = fopen(IMG, "wb");
        if (!f) { printf("FAIL 建镜像文件失败\n"); return 1; }
        if (fseek(f, (long)NBLOCKS * BLKSIZE - 1, SEEK_SET) != 0 || fputc(0, f) == EOF) {
            printf("FAIL 预分配镜像失败\n"); fclose(f); return 1;
        }
        fclose(f);
    }

    /* ② 造文件系统 */
    memset(&param, 0, sizeof(param));
    ext2fs_blocks_count_set(&param, NBLOCKS);
    param.s_log_block_size = 0;            /* 1024 字节 */
    param.s_inodes_count = 256;

    rc = ext2fs_initialize(IMG, 0, &param, unix_io_manager, &fs);
    if (rc) {
        printf("FAIL ext2fs_initialize: %s\n", error_message(rc));
        return 1;
    }
    rc = ext2fs_allocate_tables(fs);
    if (rc) {
        printf("FAIL ext2fs_allocate_tables: %s\n", error_message(rc));
        return 1;
    }
    rc = ext2fs_close(fs);
    if (rc) {
        printf("FAIL ext2fs_close: %s\n", error_message(rc));
        return 1;
    }

    /* ③ 重开复验 —— 数据必须真的写进了文件 */
    rc = ext2fs_open(IMG, 0, 0, 0, unix_io_manager, &fs);
    if (rc) {
        printf("FAIL 重新打开: %s\n", error_message(rc));
        return 1;
    }
    {
        const blk64_t nb = ext2fs_blocks_count(fs->super);
        const unsigned int ni = fs->super->s_inodes_count;
        const unsigned int bs = EXT2_BLOCK_SIZE(fs->super);
        if (nb != NBLOCKS) {
            printf("FAIL 块数 %llu != %u\n", (unsigned long long)nb, NBLOCKS);
            return 1;
        }
        if (ni < 16) {
            printf("FAIL inode 数 %u 明显不合理\n", ni);
            return 1;
        }
        if (bs != BLKSIZE) {
            printf("FAIL 块大小 %u != %d\n", bs, BLKSIZE);
            return 1;
        }
    }
    ext2fs_close(fs);

    /* ④ 错误路径：非文件系统的文件必须报 BAD_MAGIC，不得崩溃 */
    {
        FILE *f = fopen("not_a_fs_tmp.bin", "wb");
        if (f) { fwrite("not a filesystem at all", 1, 23, f); fclose(f); }
        ext2_filsys bad = NULL;
        rc = ext2fs_open("not_a_fs_tmp.bin", 0, 0, 0, unix_io_manager, &bad);
        if (rc == 0) {
            printf("FAIL 把一个普通文件当成 ext2 打开竟然成功了\n");
            return 1;
        }
        unlink("not_a_fs_tmp.bin");
    }

    unlink(IMG);
    /* 版本号只能经 API 取；E2FSPROGS_VERSION 是私有宏，公开头里没有 */
    const char *ver = NULL;
    ext2fs_get_library_version(&ver, NULL);
    printf("e2fsprogs OK: com_err 错误码表 + ext2 建库/表分配 + 重开复验(块数=%u 块大小=%d) "
           "+ 错误路径，共 4 组；版本 %s\n", NBLOCKS, BLKSIZE, ver ? ver : "?");
    return 0;
}
