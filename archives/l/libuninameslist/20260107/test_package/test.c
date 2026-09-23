/* libuninameslist/20260107 消费者测试：以库使用者身份调用公开 API，
 * 对 Unicode 名称/注解/区块接口做真实查询并断言结果。 */
#include <uninameslist.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* 'A'(U+0041) 的官方名称必须是 LATIN CAPITAL LETTER A */
    const char *name = uniNamesList_name(0x0041ul);
    if (name == NULL || strncmp(name, "LATIN CAPITAL LETTER A", 22) != 0) {
        printf("uniNamesList_name(0x41) = %s\n", name ? name : "(null)");
        return 1;
    }

    /* 注解接口可调用（U+0041 注解可能为空，仅验证链接与调用路径） */
    const char *annot = uniNamesList_annot(0x0041ul);
    (void)annot;

    int blocks = uniNamesList_blockCount();
    if (blocks <= 0) {
        printf("uniNamesList_blockCount() = %d\n", blocks);
        return 1;
    }

    /* U+0041 应落在 Basic Latin 区块（编号 0） */
    int blk = uniNamesList_blockNumber(0x0041ul);
    if (blk != 0) {
        printf("uniNamesList_blockNumber(0x41) = %d (expected 0)\n", blk);
        return 1;
    }

    const char *ver = uniNamesList_NamesListVersion();
    if (ver == NULL || ver[0] == '\0') {
        printf("uniNamesList_NamesListVersion() empty\n");
        return 1;
    }

    printf("libuninameslist consumer test OK: name(0x41)=%s blocks=%d ver=%s\n",
           name, blocks, ver);
    return 0;
}
