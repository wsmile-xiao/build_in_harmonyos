/* iortcw 1.51.c test_package — 原生场景实际执行 iowolfsp 二进制验证（R34 反空壳）。
 *
 * iortcw 是 C 应用（make 构建产出 iowolfsp 等二进制），无 C 库可链接。
 * 用法：./test_iortcw "<iowolfsp_bin_path>" —— 原生场景传入 iowolfsp 二进制路径，
 * 校验 ELF magic 并尝试执行 --version；无参数（交叉编译占位）时仅编译通过。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>  /* strchr 需此头（缺失致 Clang 15 隐式声明编译失败，AI review P0） */

static int is_elf_magic(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    unsigned char magic[4];
    size_t n = fread(magic, 1, 4, f);
    fclose(f);
    return n == 4 && magic[0] == 0x7f && magic[1] == 'E'
           && magic[2] == 'L' && magic[3] == 'F';
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        /* 交叉编译占位：无法在宿主运行 arm64 OHOS 二进制，仅编译通过（L0c 门禁） */
        printf("iortcw test_package: compile-only (cross-building placeholder)\n");
        return 0;
    }
    /* 原生场景：先校验 ELF magic（R34 反空壳），再尝试执行 --version 检查退出码 */
    const char *iowolfsp = argv[1];
    /* P3: 修正元字符检测。cmd 中路径被双引号包裹，; | & 在引号内无害；
     * 真正危险的是 " $ ` \（提前结束引号 / 变量展开 / 命令替换 / 转义） */
    if (strchr(iowolfsp, '"') || strchr(iowolfsp, '$') || strchr(iowolfsp, '`') || strchr(iowolfsp, '\\')) {
        fprintf(stderr, "iowolfsp path contains shell metacharacters: %s\n", iowolfsp);
        return 2;
    }
    if (!is_elf_magic(iowolfsp)) {
        fprintf(stderr, "iowolfsp is not a valid ELF file: %s\n", iowolfsp);
        return 3;
    }
    char cmd[1024];
    int n = snprintf(cmd, sizeof(cmd), "\"%s\" --version", iowolfsp);
    if (n < 0 || (size_t)n >= sizeof(cmd)) {
        fprintf(stderr, "iowolfsp path too long\n");
        return 4;
    }
    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "iowolfsp --version failed with exit code %d\n", ret);
        return 1;
    }
    printf("iortcw runtime test PASSED (iowolfsp --version exit 0)\n");
    return 0;
}
