/*
 * test_eibclient.c -- knxd/0.14.73 消费者功能测试（R34：真链接被测包 libeibclient）
 *
 * 署名/provenance：本文件为本归档自写的测试代码（非上游派生），只使用
 * src/include/eibclient.h 声明的公开 API，行为判据取自上游 openurl.c /
 * openlocal.c / close.c / pollfd.c / pollcomplete.c 的实现语义。
 *
 * 覆盖两类：
 *   A. NULL/错误入参守卫（EIBSocketURL/EIB_Poll_FD/EIBClose 的 -1/EINVAL 语义）
 *   B. 正向路径：本机自建 AF_UNIX 监听套接字，让 EIBSocketURL("local:<path>")
 *      真的完成 connect，并读回 EIB_Poll_FD / EIB_Poll_Complete / EIBClose。
 *      —— 这条断言只在被测库确实可用时才可能成立，产物被搬走即编不出/跑不通。
 *
 * 断言用计数器累加，末尾打印 SUMMARY total/pass/fail；有失败即非零退出。
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#include <eibclient.h>

static int total = 0;
static int passed = 0;
static int failed = 0;

static void check(const char *name, int cond)
{
    total++;
    if (cond) {
        passed++;
        printf("ok   %s\n", name);
    } else {
        failed++;
        printf("FAIL %s (errno=%d %s)\n", name, errno, strerror(errno));
    }
}

/* 建一个本机 stream 监听套接字，返回 fd；path 写入 buf（长度受 sun_path 限制）。
 * 路径放在 $HOME/tmp 而不是 cwd：conan 的 test 工作目录在缓存树里，
 * 绝对路径长度可能超过 AF_UNIX 的 sun_path 上限。 */
static int make_local_listener(char *path, size_t pathlen)
{
    const char *home = getenv("HOME");
    int fd;
    struct sockaddr_un addr;

    if (!home || !*home)
        return -1;
    snprintf(path, pathlen, "%s/tmp", home);
    mkdir(path, 0700); /* HMDFS 上 chmod 未必生效，mkdir 失败也不致命 */
    snprintf(path, pathlen, "%s/tmp/knxd-t-%ld.sock", home, (long)getpid());

    fd = socket(AF_LOCAL, SOCK_STREAM, 0);
    if (fd == -1)
        return -1;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_LOCAL;
    strncpy(addr.sun_path, path, sizeof(addr.sun_path) - 1);
    unlink(path);
    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) == -1) {
        close(fd);
        return -1;
    }
    if (listen(fd, 1) == -1) {
        close(fd);
        unlink(path);
        return -1;
    }
    return fd;
}

int main(void)
{
    char sockpath[256];
    int srv_fd;
    EIBConnection *con;

    printf("knxd libeibclient consumer test (knxd/0.14.73)\n");

    /* A1: EIBSocketURL(NULL) 必须 EINVAL 且不崩 */
    errno = 0;
    con = EIBSocketURL(NULL);
    check("A1 EIBSocketURL(NULL) returns NULL", con == NULL);
    check("A2 EIBSocketURL(NULL) sets errno=EINVAL", errno == EINVAL);

    /* A3: 未知 URL 前缀同样走 EINVAL 分支 */
    errno = 0;
    con = EIBSocketURL("bogus:whatever");
    check("A3 EIBSocketURL(unknown prefix) returns NULL", con == NULL);
    check("A4 EIBSocketURL(unknown prefix) sets errno=EINVAL", errno == EINVAL);

    /* A5: 守卫型 API 对 NULL 的返回值语义 */
    errno = 0;
    check("A5 EIB_Poll_FD(NULL) == -1", EIB_Poll_FD(NULL) == -1);
    errno = 0;
    check("A6 EIBClose(NULL) == -1", EIBClose(NULL) == -1);

    /* A7: 连到不存在的本机套接字必须失败（connect 返回 -1 -> 库返回 NULL） */
    con = EIBSocketLocal("/tmp/knxd-does-not-exist-01473");
    check("A7 EIBSocketLocal(missing path) returns NULL", con == NULL);

    /* B: 正向路径 —— 自建监听套接字后让库真连接 */
    srv_fd = make_local_listener(sockpath, sizeof(sockpath));
    if (srv_fd < 0) {
        printf("skip B1..B4 (cannot prepare local listener: errno=%d %s)\n",
               errno, strerror(errno));
    } else {
        char url[300];
        snprintf(url, sizeof(url), "local:%s", sockpath);
        errno = 0;
        con = EIBSocketURL(url);
        check("B1 EIBSocketURL(local:<live socket>) connects", con != NULL);
        if (con) {
            check("B2 EIB_Poll_FD(con) returns usable fd", EIB_Poll_FD(con) >= 0);
            errno = 0;
            check("B3 EIB_Poll_Complete(con) == 0 (no pending request)",
                  EIB_Poll_Complete(con) == 0);
            check("B4 EIBClose(con) == 0", EIBClose(con) == 0);
        }
        close(srv_fd);
        unlink(sockpath);
    }

    printf("SUMMARY total=%d pass=%d fail=%d\n", total, passed, failed);
    return failed == 0 ? 0 : 1;
}
