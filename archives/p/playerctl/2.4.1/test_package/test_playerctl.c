/* test_playerctl.c — playerctl 2.4.1 test_package 消费者测试（OHOS aarch64）
 *
 * R34：必须实质依赖被测包，本测试同时覆盖两条真实消费路径 ——
 *   A) 编译期：公开头文件 <playerctl/playerctl.h> 的版本契约
 *   B) 链接期：从 libplayerctl.so 解析公共 GObject 类型注册符号
 *   C) 运行期：真实调用 playerctl_player_name_copy()/free() 的深拷贝语义
 *   D) 执行安装后的 bin/playerctl、bin/playerctld（消费者实际使用路径）
 *
 * OHOS 约束（实测，见 notes.md）：
 *   * 不写临时文件（/tmp 只读；$TMPDIR 不保证存在）——本测试全程只用内存与管道。
 *   * 不调用 system()/popen()（OHOS 无 /bin/sh），一律 fork + execv。
 *   * 被测 ELF 无 RUNPATH → 运行时依赖 conanrun（VirtualRunEnv）导出的
 *     LD_LIBRARY_PATH 才能加载 libplayerctl.so.2 / libglib-2.0.so.0。
 *
 * 退出码：0=全部断言通过；1=有断言失败；2=用法错误。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#include <glib.h>
#include <playerctl/playerctl.h>

static int g_failures;

#define CHECK(label, cond, detail)                                             \
    do {                                                                       \
        if (cond) {                                                            \
            printf("PASS %s: %s\n", (label), (detail));                        \
        } else {                                                               \
            printf("FAIL %s: %s\n", (label), (detail));                        \
            g_failures++;                                                      \
        }                                                                      \
        fflush(stdout);                                                        \
    } while (0)

/* fork + execv：不依赖 shell，不做字符串拼接，避免注入与 /bin/sh 依赖。 */
static int run_capture(const char *path, char *const argv[], char *out,
                       size_t outsz)
{
    int fds[2];
    pid_t pid;
    size_t used = 0;
    int status = 0;

    if (pipe(fds) != 0) {
        return -1;
    }
    pid = fork();
    if (pid < 0) {
        close(fds[0]);
        close(fds[1]);
        return -1;
    }
    if (pid == 0) {
        close(fds[0]);
        if (dup2(fds[1], STDOUT_FILENO) < 0 || dup2(fds[1], STDERR_FILENO) < 0) {
            _exit(126);
        }
        close(fds[1]);
        execv(path, argv);
        _exit(127);
    }
    close(fds[1]);
    for (;;) {
        ssize_t n = read(fds[0], out + used, outsz - 1 - used);
        if (n <= 0) {
            break;
        }
        used += (size_t)n;
        if (used + 1 >= outsz) {
            break;
        }
    }
    out[used] = '\0';
    close(fds[0]);
    if (waitpid(pid, &status, 0) < 0 || !WIFEXITED(status)) {
        return -1;
    }
    return WEXITSTATUS(status);
}

int main(int argc, char *argv[])
{
    const char *bindir;
    const char *k_name = "org.mpris.MediaPlayer2.playerctl-ohos";
    gchar *name_buf;
    gchar *instance_buf;
    PlayerctlPlayerName source_name;
    PlayerctlPlayerName *copied;
    GType name_type;
    GType source_type;
    char path[4096];
    char out[16384];
    char *child_argv[3];
    int rc;

    if (argc < 2) {
        printf("FAIL args: usage: test_playerctl <package_bindir>\n");
        return 2;
    }
    bindir = argv[1];

    /* ── A. 编译期 API 契约（公开头文件的版本宏） ───────────────────────── */
    CHECK("A1", strcmp(PLAYERCTL_VERSION_S, "2.4.1") == 0,
          "PLAYERCTL_VERSION_S == \"2.4.1\"");
    CHECK("A2", PLAYERCTL_MAJOR_VERSION == 2 && PLAYERCTL_MINOR_VERSION == 4
                    && PLAYERCTL_MICRO_VERSION == 1,
          "PLAYERCTL_{MAJOR,MINOR,MICRO}_VERSION == 2.4.1");
    CHECK("A3", PLAYERCTL_CHECK_VERSION(2, 4, 1) && !PLAYERCTL_CHECK_VERSION(2, 5, 0),
          "PLAYERCTL_CHECK_VERSION(2,4,1) true, (2,5,0) false");

    /* ── B. 链接期：公共 GObject 类型注册（符号由 libplayerctl.so 提供） ── */
    name_type = playerctl_player_name_get_type();
    CHECK("B1", name_type != 0, "playerctl_player_name_get_type() != 0");
    CHECK("B2", g_type_name(name_type) != NULL
                    && strcmp(g_type_name(name_type), "PlayerctlPlayerName") == 0,
          "boxed type registered as PlayerctlPlayerName");

    source_type = playerctl_source_get_type();
    CHECK("B3", source_type != 0 && G_TYPE_IS_ENUM(source_type),
          "playerctl_source_get_type() is a registered GEnum");

    /* ── C. 运行期：真实调用公共 API 的深拷贝 / 释放语义 ───────────────── */
    name_buf = g_strdup(k_name);
    instance_buf = g_strdup("org.mpris.MediaPlayer2.playerctl-ohos.instance");
    source_name.name = name_buf;
    source_name.instance = instance_buf;
    source_name.source = PLAYERCTL_SOURCE_DBUS_SESSION;

    copied = playerctl_player_name_copy(&source_name);
    CHECK("C1", copied != NULL, "playerctl_player_name_copy() returns non-NULL");
    if (copied != NULL) {
        CHECK("C2", copied != &source_name, "copy is a distinct allocation");
        CHECK("C3", copied->name != NULL && copied->name != name_buf
                        && strcmp(copied->name, name_buf) == 0,
              "copy->name is a fresh deep copy of the source string");
        CHECK("C4", copied->instance != NULL && copied->instance != instance_buf
                        && strcmp(copied->instance, instance_buf) == 0,
              "copy->instance is a fresh deep copy of the source string");
        CHECK("C5", copied->source == PLAYERCTL_SOURCE_DBUS_SESSION,
              "copy->source preserved (PLAYERCTL_SOURCE_DBUS_SESSION)");
        /* 深拷贝证据：改写源串首字符，副本必须不受影响 */
        name_buf[0] = 'X';
        CHECK("C6", strcmp(copied->name, k_name) == 0,
              "mutating the source string leaves the copy untouched");
        playerctl_player_name_free(copied);
    }
    g_free(name_buf);
    g_free(instance_buf);

    /* ── D. 执行被测包安装的二进制 ─────────────────────────────────────── */
    snprintf(path, sizeof(path), "%s/playerctl", bindir);
    CHECK("D1", access(path, X_OK) == 0, "bin/playerctl exists and is executable");

    child_argv[0] = path;
    child_argv[1] = "--version";
    child_argv[2] = NULL;
    rc = run_capture(path, child_argv, out, sizeof(out));
    CHECK("D2", rc == 0, "playerctl --version exits 0");
    CHECK("D3", strstr(out, "v2.4.1") != NULL,
          "playerctl --version prints \"v2.4.1\"");
    if (strstr(out, "v2.4.1") == NULL) {
        printf("     raw output: %s\n", out);
    }

    child_argv[1] = "--help";
    rc = run_capture(path, child_argv, out, sizeof(out));
    CHECK("D4", rc == 0, "playerctl --help exits 0");
    CHECK("D5", strstr(out, "Controller for media players") != NULL
                    && strstr(out, "--player=NAME") != NULL,
          "playerctl --help exposes the upstream option surface");

    snprintf(path, sizeof(path), "%s/playerctld", bindir);
    CHECK("D6", access(path, X_OK) == 0, "bin/playerctld exists and is executable");

    child_argv[0] = path;
    child_argv[1] = "--help";
    rc = run_capture(path, child_argv, out, sizeof(out));
    CHECK("D7", rc == 0 && strstr(out, "Playerctl Daemon") != NULL,
          "playerctld --help exits 0 and reports the daemon usage");

    printf("SUMMARY: %d failed\n", g_failures);
    if (g_failures != 0) {
        printf("TEST_PLAYERCTL_FAIL\n");
        return 1;
    }
    printf("TEST_PLAYERCTL_PASS\n");
    return 0;
}
