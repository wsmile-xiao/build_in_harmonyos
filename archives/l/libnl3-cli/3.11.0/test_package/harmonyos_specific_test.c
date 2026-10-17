/* HarmonyOS 平台特定消费者测试 — libnl3-cli 3.11.0
 *
 * 编译期硬绑定：__OHOS__ + __aarch64__（防误用非鸿蒙工具链编译通过）。
 * 运行期真实链接 libnl-cli-3（shared，DT_NEEDED 自动拉齐 nl-route-3 / nl-genl-3 /
 * nl-nf-3 / nl-idiag-3 / nl-xfrm-3 / nl-3），验证鸿蒙 musl 工具链下
 * libnl3-cli 的消费者可用性：
 *
 *   1) E316/E492/E505 SONAME 实体化验证：dlopen 包内 lib/libnl-cli-3.so.200
 *      —— 若 package() 未把 SONAME 软链实体化，OHOS musl 加载器 open 软链
 *      EACCES，本用例即失败；
 *   2) dlopen 插件机制：包内 lib/libnl/cli/qdisc/htb.so 与 cls/basic.so 以
 *      RTLD_NOW 加载（插件引用的 nl_cli_* 与 nl_* 符号从已加载的 shared libnl
 *      解析 —— 这正是本包固定 shared 交付的原因）；
 *   3) 纯用户态解析 API（musl ABI）：nl_cli_parse_u32 往返、nl_addr_parse
 *      "10.0.0.1/24" 的前缀长度与二进制地址断言（不触碰 netlink socket）；
 *   4) 端到端动态加载链：fork + exec 包内 bin/nl-util-addr（无参数）——
 *      能走到 main 打印 Usage 并以退出码 255 结束，即证明 48 个工具的
 *      DT_NEEDED 全链（libnl-cli-3 + 6 子库）在包内可解析。
 *
 * 环境变量（由 test_package/conanfile.py 注入）：
 *   NL3CLI_LIB_DIR — 包内 lib 目录（含 libnl-cli-3.so.200 与 cli/ 插件树）
 *   NL3CLI_BIN_DIR — 包内 bin 目录（48 个工具）
 */
#include <dlfcn.h>
#include <netlink/addr.h>
#include <netlink/cli/utils.h>
#include <sys/wait.h>
#include <unistd.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if !defined(__OHOS__)
#error "This test must be compiled with the OpenHarmony toolchain (__OHOS__ undefined)"
#endif

#if !defined(__aarch64__)
#error "HarmonyOS target must be aarch64 (__aarch64__ undefined)"
#endif

static int g_failures = 0;

static void check(int cond, const char *what)
{
    printf("%s %s\n", cond ? "PASS:" : "FAIL:", what);
    if (!cond)
        ++g_failures;
}

int main(void)
{
    printf("HarmonyOS-specific libnl3-cli consumer test (libnl3-cli/3.11.0)\n");

    const char *lib_dir = getenv("NL3CLI_LIB_DIR");
    const char *bin_dir = getenv("NL3CLI_BIN_DIR");
    check(lib_dir != NULL && lib_dir[0] != '\0', "env NL3CLI_LIB_DIR is set");
    check(bin_dir != NULL && bin_dir[0] != '\0', "env NL3CLI_BIN_DIR is set");
    if (!lib_dir || !bin_dir)
        return 1;

    /* ---- 1) E316/E492/E505：SONAME 实体文件可被 musl 加载器打开 ---- */
    char path[512];
    snprintf(path, sizeof(path), "%s/libnl-cli-3.so.200", lib_dir);
    void *cli_handle = dlopen(path, RTLD_NOW);
    if (!cli_handle)
        printf("  dlerror: %s\n", dlerror());
    check(cli_handle != NULL,
          "dlopen(libnl-cli-3.so.200) loads the materialized SONAME file");

    /* ---- 2) dlopen 插件（RTLD_NOW 符号从 shared libnl 解析）---- */
    snprintf(path, sizeof(path), "%s/libnl/cli/qdisc/htb.so", lib_dir);
    void *plug_htb = dlopen(path, RTLD_NOW);
    if (!plug_htb)
        printf("  dlerror: %s\n", dlerror());
    check(plug_htb != NULL, "dlopen(cli/qdisc/htb.so) plugin loads with RTLD_NOW");

    snprintf(path, sizeof(path), "%s/libnl/cli/cls/basic.so", lib_dir);
    void *plug_basic = dlopen(path, RTLD_NOW);
    if (!plug_basic)
        printf("  dlerror: %s\n", dlerror());
    check(plug_basic != NULL, "dlopen(cli/cls/basic.so) plugin loads with RTLD_NOW");
    if (plug_htb)
        dlclose(plug_htb);
    if (plug_basic)
        dlclose(plug_basic);

    /* ---- 3) 纯用户态解析 API（musl ABI，不触碰 netlink socket）---- */
    check(nl_cli_parse_u32("3141592653") == 3141592653u,
          "nl_cli_parse_u32(\"3141592653\") round-trips");

    struct nl_addr *addr = NULL;
    int err = nl_addr_parse("10.0.0.1/24", AF_INET, &addr);
    check(err == 0 && addr != NULL, "nl_addr_parse(\"10.0.0.1/24\") succeeds");
    if (addr) {
        check(nl_addr_get_prefixlen(addr) == 24, "prefix length is 24");
        const unsigned char *octets =
            (const unsigned char *)nl_addr_get_binary_addr(addr);
        check(octets != NULL && octets[0] == 10 && octets[1] == 0 &&
                  octets[2] == 0 && octets[3] == 1,
              "binary address is 10.0.0.1");
        nl_addr_put(addr);
    }

    /* ---- 4) 端到端动态加载链：exec 包内工具（Usage 路径，退出码 255）---- */
    snprintf(path, sizeof(path), "%s/nl-util-addr", bin_dir);
    pid_t pid = fork();
    check(pid >= 0, "fork() succeeds");
    if (pid == 0) {
        execl(path, "nl-util-addr", (char *)NULL);
        _exit(127); /* exec 失败（工具缺失或 DT_NEEDED 无法解析） */
    }
    int status = -1;
    if (pid > 0)
        waitpid(pid, &status, 0);
    int exited = WIFEXITED(status);
    int code = exited ? WEXITSTATUS(status) : -1;
    check(exited && code == 255,
          "exec(nl-util-addr) reaches main() and exits 255 on Usage path");

    printf("HarmonyOS-specific consumer test: %d failure(s)\n", g_failures);
    return g_failures == 0 ? 0 : 1;
}
