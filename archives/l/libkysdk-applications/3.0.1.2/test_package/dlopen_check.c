/* 消费者 dlopen 实测辅助程序（普通 exec 二进制，非 AppSpawn 启动）。
 *
 * 在 test_package build() 阶段以构建 uid（产物属主 20001006）上下文执行，
 * 严格验证 4 个 .so 可加载（DT_NEEDED 依赖解析 + 代码映射）；任一失败即
 * 退出码 1（build 失败），无 ELF 魔数回退（R9/R34）。
 *
 * 背景（CI #49631-#49714 实证）：python3 经 AppSpawn 恒以 app uid
 * （20020101/20020102）运行，而 HMDFS 缓存产物属主为构建 uid 20001006、
 * mode 750（other 位被裁），跨 uid dlopen 恒 EACCES 且 chown/chmod
 * （含属主上下文）均静默无效——python 探针在任意 conan 阶段都无法加载；
 * 编译期/构建期普通 exec 二进制（qmake/clang/lld 及 82 个上游 QTest 测试
 * 二进制）可读取缓存库并运行，故以本程序在 build() 阶段做真实加载验证。
 */
#include <dlfcn.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <lib.so> [<lib.so> ...]\n", argv[0]);
        return 2;
    }
    fprintf(stderr, "dlopen_check uid=%d euid=%d\n",
            (int)getuid(), (int)geteuid());
    for (int i = 1; i < argc; i++) {
        struct stat st;
        if (stat(argv[i], &st) == 0)
            fprintf(stderr, "  %s: uid=%d mode=%o\n", argv[i],
                    (int)st.st_uid, st.st_mode & 07777);
        void *h = dlopen(argv[i], RTLD_NOW);
        if (!h) {
            fprintf(stderr, "  dlopen FAIL %s: %s\n", argv[i], dlerror());
            return 1;
        }
        fprintf(stderr, "  dlopen OK %s\n", argv[i]);
        dlclose(h);
    }
    printf("dlopen_check: %d libs loaded OK\n", argc - 1);
    return 0;
}
