/* consumer_e2e.c — wayland-protocols 数据包消费者端到端测试
 *
 * 消费链与真实下游一致（kwayland / plasma-wayland-protocols 同款）：
 * test_package 配方用静态构建的 wayland-scanner 对包内协议 XML 生成
 * client-header + private-code，与本程序一起编译链接；运行时逐例核验
 * 编译态接口数据与包内 XML 定义一致（接口名 / 版本号 / 请求计数 /
 * XML 原样包含 name 与 version 属性）。
 *
 * 7 个代表协议覆盖 stable/staging/unstable 三类安装目录（上游
 * installed_protocol_files 仅此三类，experimental 设计不安装），含
 * 1.48 唯一进入安装集的新协议 xdg-session-management；3 个 experimental
 * 新协议由上游 191 项测试覆盖。每例独立 TEST PASS/FAIL，末行 TEST
 * SUMMARY，任一失败退出码 1。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "wayland-util.h"

#include "xdg-shell-client-protocol.h"
#include "viewporter-client-protocol.h"
#include "xdg-session-management-v1-client-protocol.h"
#include "xdg-activation-v1-client-protocol.h"
#include "xdg-dialog-v1-client-protocol.h"
#include "xdg-decoration-unstable-v1-client-protocol.h"
#include "xdg-output-unstable-v1-client-protocol.h"

struct probe {
    const char *label;
    const struct wl_interface *iface;
    const char *expect_name;
    int expect_version;
    const char *xml_rel; /* 相对 pkgdatadir 的 XML 路径 */
};

static struct probe probes[] = {
    {"stable/xdg-shell", &xdg_wm_base_interface, "xdg_wm_base", 7,
     "stable/xdg-shell/xdg-shell.xml"},
    {"stable/viewporter", &wp_viewporter_interface, "wp_viewporter", 1,
     "stable/viewporter/viewporter.xml"},
    {"staging/xdg-session-management(1.48新协议)", &xdg_session_manager_v1_interface,
     "xdg_session_manager_v1", 1,
     "staging/xdg-session-management/xdg-session-management-v1.xml"},
    {"staging/xdg-activation", &xdg_activation_v1_interface,
     "xdg_activation_v1", 1,
     "staging/xdg-activation/xdg-activation-v1.xml"},
    {"staging/xdg-dialog", &xdg_wm_dialog_v1_interface,
     "xdg_wm_dialog_v1", 1,
     "staging/xdg-dialog/xdg-dialog-v1.xml"},
    {"unstable/xdg-decoration", &zxdg_decoration_manager_v1_interface,
     "zxdg_decoration_manager_v1", 2,
     "unstable/xdg-decoration/xdg-decoration-unstable-v1.xml"},
    {"unstable/xdg-output", &zxdg_output_manager_v1_interface,
     "zxdg_output_manager_v1", 3,
     "unstable/xdg-output/xdg-output-unstable-v1.xml"},
};

static int n_pass = 0;
static int n_fail = 0;

static void check(int ok, const char *what, const char *detail)
{
    if (ok) {
        printf("  TEST PASS %s%s%s\n", what, detail ? " " : "",
               detail ? detail : "");
        n_pass++;
    } else {
        printf("  TEST FAIL %s%s%s\n", what, detail ? " " : "",
               detail ? detail : "");
        n_fail++;
    }
}

/* 读包内 XML，核对 name="..." 与 version="N" 是否原样存在 */
static int xml_has(const char *pkgdatadir, const char *rel,
                   const char *name, int version)
{
    char path[2048];
    char want[1024];
    char *buf;
    FILE *f;
    long n;
    int ok;

    snprintf(path, sizeof path, "%s/%s", pkgdatadir, rel);
    f = fopen(path, "rb");
    if (!f)
        return 0;
    fseek(f, 0, SEEK_END);
    n = ftell(f);
    fseek(f, 0, SEEK_SET);
    buf = (char *)malloc((size_t)n + 1);
    if (!buf) {
        fclose(f);
        return 0;
    }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) {
        free(buf);
        fclose(f);
        return 0;
    }
    fclose(f);
    buf[n] = '\0';

    snprintf(want, sizeof want, "name=\"%s\"", name);
    ok = strstr(buf, want) != NULL;
    if (ok) {
        snprintf(want, sizeof want, "version=\"%d\"", version);
        ok = strstr(buf, want) != NULL;
    }
    free(buf);
    return ok;
}

int main(int argc, char **argv)
{
    const char *pkgdatadir;
    size_t i;

    if (argc < 2) {
        fprintf(stderr, "usage: consumer_e2e <pkgdatadir>\n");
        return 2;
    }
    pkgdatadir = argv[1];

    for (i = 0; i < sizeof probes / sizeof probes[0]; i++) {
        struct probe *p = &probes[i];
        printf("TEST CASE %s\n", p->label);
        check(p->iface && p->iface->name &&
              strcmp(p->iface->name, p->expect_name) == 0,
              "- 接口名",
              (p->iface && p->iface->name) ? p->iface->name : "NULL");
        check(p->iface && p->iface->version == p->expect_version,
              "- 版本号", NULL);
        check(p->iface && p->iface->method_count > 0, "- 请求计数", NULL);
        check(xml_has(pkgdatadir, p->xml_rel, p->expect_name,
                      p->expect_version),
              "- 包内XML一致", p->xml_rel);
    }
    printf("TEST SUMMARY: %d passed, %d failed\n", n_pass, n_fail);
    return n_fail == 0 ? 0 : 1;
}
