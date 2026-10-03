/*
 * HarmonyOS-specific runtime closure test for spice 0.16.0 (libspice-server).
 *
 * glibc / bionic 与 musl 在 rpath、soname 链接、libc++ 运行时上的行为不同：
 * libspice-server.so 的 DT_NEEDED 闭包横跨 Conan 制品（glib / pixman / openssl /
 * libjpeg / zlib / lz4）与 OHOS 系统库（libc / libc++_shared）。本测试在 OHOS
 * 加载器下实际解析整条闭包，并通过 loader 路径真实调用导出的 C ABI（不只是
 * 符号存在，而是可执行）。
 *
 * Checks
 *   1. <package>/lib 下每个真实（非 symlink）发布的共享库均可 dlopen(RTLD_NOW)
 *   2. 至少存在 1 个共享库（包内运行时闭包入口 libspice-server.so）
 *   3. libspice-server.so 仍可加载（闭包驻留后）
 *   4. 消费者契约符号可经 dlsym 解析（spice_server_new/destroy/set_port/
 *      set_ticket/set_name）
 *   5. 经 loader 路径真实调用 spice_server_new() → 返回实例 → destroy()
 *
 * 每个用例输出 "TEST PASS - ..." / "TEST FAIL - ..."，结尾输出
 * "TEST SUMMARY: N/N passed"；任一失败进程退出码 1。
 *
 * Usage: test_ohos_runtime <path-to-libspice-server.so>
 */
#include <dirent.h>
#include <dlfcn.h>
#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define MAX_FILES 64

static int tests_run = 0;
static int tests_failed = 0;

static void check(int cond, const char *what)
{
    tests_run++;
    if (cond) {
        printf("TEST PASS - %s\n", what);
    } else {
        printf("TEST FAIL - %s\n", what);
        tests_failed++;
    }
    fflush(stdout);
}

static int is_shared_lib(const char *name)
{
    return strstr(name, ".so") != NULL;
}

int main(int argc, char **argv)
{
    char path_buf[4096];
    char dir_buf[4096];
    const char *libdir;
    DIR *dir;
    struct dirent *entry;
    int nreal = 0, nloaded = 0;
    void *handle;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-libspice-server.so>\n", argv[0]);
        return 2;
    }

    /* <pkg>/lib/libspice-server.so -> <pkg>/lib */
    snprintf(path_buf, sizeof(path_buf), "%s", argv[1]);
    snprintf(dir_buf, sizeof(dir_buf), "%s", dirname(path_buf));
    libdir = dir_buf;
    printf("info - packaged lib dir: %s\n", libdir);

    dir = opendir(libdir);
    if (dir == NULL) {
        perror("opendir");
        return 2;
    }

    while ((entry = readdir(dir)) != NULL) {
        char full[4096];
        struct stat st;

        if (!is_shared_lib(entry->d_name)) {
            continue;
        }
        snprintf(full, sizeof(full), "%s/%s", libdir, entry->d_name);
        if (lstat(full, &st) != 0) {
            continue;
        }
        if (S_ISLNK(st.st_mode)) {
            /* the soname symlinks are covered by loading the real file */
            continue;
        }
        nreal++;
        if (nreal > MAX_FILES) {
            break;
        }
        handle = dlopen(full, RTLD_NOW | RTLD_LOCAL);
        if (handle != NULL) {
            printf("TEST PASS - OHOS loader dlopen(RTLD_NOW): %s\n", entry->d_name);
            tests_run++;
            nloaded++;
            dlclose(handle);
        } else {
            printf("TEST FAIL - OHOS loader dlopen(RTLD_NOW): %s -> %s\n",
                   entry->d_name, dlerror());
            tests_run++;
            tests_failed++;
        }
    }
    closedir(dir);

    check(nreal >= 1,
          "packaged runtime closure present (>= 1 shared library)");
    printf("info - packaged shared libraries: %d found, %d loaded\n", nreal, nloaded);

    /* Reload the main artifact (the closure stays resident) and exercise the
     * exported C ABI through the loader path, not just symbol presence. */
    handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    check(handle != NULL,
          "libspice-server still loads with RTLD_NOW after the closure is resident");
    if (handle != NULL) {
        void *sym_new = dlsym(handle, "spice_server_new");
        void *sym_destroy = dlsym(handle, "spice_server_destroy");
        void *sym_set_port = dlsym(handle, "spice_server_set_port");
        void *sym_set_ticket = dlsym(handle, "spice_server_set_ticket");
        void *sym_set_name = dlsym(handle, "spice_server_set_name");
        check(sym_new != NULL && sym_destroy != NULL && sym_set_port != NULL
                  && sym_set_ticket != NULL && sym_set_name != NULL,
              "consumer contract symbols resolvable at runtime "
              "(spice_server_new/destroy/set_port/set_ticket/set_name)");
        if (sym_new != NULL && sym_destroy != NULL && sym_set_port != NULL
            && sym_set_ticket != NULL && sym_set_name != NULL) {
            typedef void *(*new_fn)(void);
            typedef void (*destroy_fn)(void *);
            typedef int (*set_port_fn)(void *, int);
            typedef int (*set_ticket_fn)(void *, const char *, int, int, int);
            typedef void (*set_name_fn)(void *, const char *);
            new_fn server_new = (new_fn)sym_new;
            destroy_fn server_destroy = (destroy_fn)sym_destroy;
            set_port_fn server_set_port = (set_port_fn)sym_set_port;
            set_ticket_fn server_set_ticket = (set_ticket_fn)sym_set_ticket;
            set_name_fn server_set_name = (set_name_fn)sym_set_name;
            void *server = server_new();
            int ok = (server != NULL);
            if (ok) {
                ok = server_set_port(server, 5912) == 0;
                server_set_name(server, "spice-ohos-runtime-test");
                ok = ok && server_set_ticket(server, "ohos-tp-ticket", 0, 1, 1) == 0;
                server_destroy(server);
            }
            check(ok, "API callable via loader path "
                      "(new -> set_port/set_name/set_ticket -> destroy)");
        } else {
            check(0, "API callable via loader path "
                     "(new -> set_port/set_name/set_ticket -> destroy)");
        }
        dlclose(handle);
    } else {
        fprintf(stderr, "dlopen(%s) failed: %s\n", argv[1], dlerror());
    }

    printf("TEST SUMMARY: %d/%d passed\n", tests_run - tests_failed, tests_run);
    return tests_failed == 0 ? 0 : 1;
}
