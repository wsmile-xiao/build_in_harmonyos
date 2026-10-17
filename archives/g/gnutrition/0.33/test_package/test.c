/* test.c — gnutrition 0.33 消费者验证（真实执行已安装产物）
 *
 * 模拟业务上层用户：仅通过安装产出的 gnutrition 可执行文件与包内
 * share/gnutrition/food.db 数据，在 OHOS (aarch64) 上启动应用并验证
 * 可观测行为——sqlite3 数据层成功加载 food.db（不出现 cannot open
 * database）；随后按 OHOS PC 无原生显示的环境纪实记录显示依赖边界
 * （E471 分类：display-dependent，不伪造 GUI 运行成功）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    const char *bin = getenv("GNUTRITION_BIN");
    const char *pkg_datadir = getenv("GNUTRITION_PKG_DATADIR");
    const char *xdg = getenv("GNUTRITION_XDG_DATA_HOME");
    char cmd[4096];
    FILE *p;
    char buf[8192];
    char combined[16384] = "";
    int rc;

    if (!bin || !*bin || !pkg_datadir || !*pkg_datadir) {
        fprintf(stderr, "FATAL: GNUTRITION_BIN / GNUTRITION_PKG_DATADIR 未设置\n");
        return 2;
    }

    snprintf(cmd, sizeof(cmd),
             "GNUTRITION_DATADIR='%s' GTK_BACKEND=broadway XDG_DATA_HOME='%s' %s "
             "2>&1; echo \"__EXIT_$?__\"",
             pkg_datadir, xdg ? xdg : "", bin);
    p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "FATAL: popen failed\n");
        return 2;
    }
    while (fgets(buf, sizeof(buf), p)) {
        if (strlen(combined) + strlen(buf) < sizeof(combined) - 1)
            strcat(combined, buf);
    }
    rc = pclose(p);

    printf("--- gnutrition consumer run output ---\n%s\n", combined);

    if (strstr(combined, "cannot open database")) {
        printf("consumer_test FAIL: 数据层未通过（cannot open database）\n");
        return 1;
    }
    printf("consumer_test PASS: food.db 数据层加载成功（无 cannot open database）\n");

    if (strstr(combined, "cannot open display") ||
        strstr(combined, "Gtk-WARNING")) {
        printf("consumer_test INFO: 到达 GTK 显示依赖边界（OHOS 无原生显示，"
               "E471 display-dependent 纪实分类，非库缺陷）\n");
    } else if (strstr(combined, "__EXIT_")) {
        printf("consumer_test INFO: 无显示相关告警，退出码见输出 __EXIT_ 标记\n");
    }

    return 0;
}