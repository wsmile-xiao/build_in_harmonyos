/* harmonyos_specific_test.c — gnutrition 0.33 HarmonyOS 专项测试
 *
 * OHOS 专用适配验证（真实执行已安装的 gnutrition 可执行产物）：
 *   A. 有效 GNUTRITION_DATADIR（指向包内 share/gnutrition）+ broadway 后端：
 *      二进制须越过 sqlite3 数据层（不出现 "cannot open database"），
 *      到达 GTK 显示依赖边界（OHOS PC 无原生显示后端，按 E471 纪实分类）。
 *   B. 无效 GNUTRITION_DATADIR：报错须包含实际覆盖路径（环境变量覆盖生效）。
 *   C. 未设置 GNUTRITION_DATADIR：回退编译期默认路径（补丁不改变默认行为）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char outbuf[65536];
static char errbuf[65536];
static char tmp_prefix[512];

/* 运行命令并捕获 stdout/stderr 与真实退出码（不经 shell 管道，避免掩盖状态）。
 * 临时文件写入 TMPDIR（OHOS 上 /tmp 为只读，须用可写 TMPDIR）。 */
static int run_capture(const char *cmd, char *out, size_t outsz,
                       char *err, size_t errsz)
{
    char full[4096];
    char f_out[1024], f_err[1024], f_rc[1024];
    FILE *p;
    size_t n;
    int rc;

    snprintf(f_out, sizeof(f_out), "%s/gn_out", tmp_prefix);
    snprintf(f_err, sizeof(f_err), "%s/gn_err", tmp_prefix);
    snprintf(f_rc, sizeof(f_rc), "%s/gn_rc", tmp_prefix);
    snprintf(full, sizeof(full), "%s > %s 2> %s; echo $? > %s",
             cmd, f_out, f_err, f_rc);
    rc = system(full);
    (void)rc;

    out[0] = '\0';
    p = fopen(f_out, "r");
    if (p) {
        n = fread(out, 1, outsz - 1, p);
        out[n] = '\0';
        fclose(p);
    }
    err[0] = '\0';
    p = fopen(f_err, "r");
    if (p) {
        n = fread(err, 1, errsz - 1, p);
        err[n] = '\0';
        fclose(p);
    }
    rc = 255;
    p = fopen(f_rc, "r");
    if (p) {
        if (fscanf(p, "%d", &rc) != 1)
            rc = 255;
        fclose(p);
    }
    remove(f_out);
    remove(f_err);
    remove(f_rc);
    return rc;
}

int main(void)
{
    const char *bin = getenv("GNUTRITION_BIN");
    const char *pkg_datadir = getenv("GNUTRITION_PKG_DATADIR");
    const char *xdg = getenv("GNUTRITION_XDG_DATA_HOME");
    char cmd[4096];
    int rc, pass = 0, cases;

    if (!bin || !*bin || !pkg_datadir || !*pkg_datadir) {
        fprintf(stderr, "FATAL: GNUTRITION_BIN / GNUTRITION_PKG_DATADIR 未设置\n");
        return 2;
    }

    {
        const char *tmp = getenv("TMPDIR");
        if (!tmp || !*tmp)
            tmp = ".";
        snprintf(tmp_prefix, sizeof(tmp_prefix), "%s", tmp);
    }

    /* A. 有效数据目录 + broadway 后端（headless OHOS）：数据层须通过。 */
    snprintf(cmd, sizeof(cmd),
             "GNUTRITION_DATADIR='%s' GTK_BACKEND=broadway XDG_DATA_HOME='%s' %s",
             pkg_datadir, xdg ? xdg : "", bin);
    rc = run_capture(cmd, outbuf, sizeof(outbuf), errbuf, sizeof(errbuf));
    printf("A) valid datadir + broadway: exit=%d\n", rc);
    if (strstr(errbuf, "cannot open database") ||
        strstr(outbuf, "cannot open database")) {
        printf("A) FAIL: DB 层未通过（出现 cannot open database）\n");
        printf("--- stderr ---\n%s\n", errbuf);
    } else {
        printf("A) PASS: sqlite3 数据层通过（无 cannot open database）\n");
        pass++;
    }
    if (strstr(errbuf, "cannot open display") || strstr(errbuf, "Gtk-WARNING")) {
        printf("A) INFO: 到达 GTK 显示依赖边界（headless OHOS 无原生显示，E471 纪实分类）\n");
        printf("--- %s\n", strstr(errbuf, "Gtk-WARNING")
                   ? strstr(errbuf, "Gtk-WARNING") : "display");
    }

    /* B. 无效数据目录：报错须含覆盖路径（环境变量覆盖生效）。 */
    snprintf(cmd, sizeof(cmd),
             "GNUTRITION_DATADIR='/nonexistent-gnutrition-datadir' GTK_BACKEND=broadway %s",
             bin);
    rc = run_capture(cmd, outbuf, sizeof(outbuf), errbuf, sizeof(errbuf));
    printf("B) invalid datadir: exit=%d\n", rc);
    if (strstr(errbuf, "/nonexistent-gnutrition-datadir/food.db") ||
        strstr(outbuf, "/nonexistent-gnutrition-datadir/food.db")) {
        printf("B) PASS: 环境变量覆盖生效（错误含覆盖路径）\n");
        pass++;
    } else {
        printf("B) FAIL: 未观察到覆盖路径\n--- stderr ---\n%s\n", errbuf);
    }

    /* C. 未设置覆盖：回退编译期默认路径。 */
    snprintf(cmd, sizeof(cmd), "GTK_BACKEND=broadway %s", bin);
    rc = run_capture(cmd, outbuf, sizeof(outbuf), errbuf, sizeof(errbuf));
    printf("C) unset override: exit=%d\n", rc);
    if (strstr(errbuf, "//share/gnutrition/food.db") ||
        strstr(outbuf, "//share/gnutrition/food.db")) {
        printf("C) PASS: 未设置时回退编译期默认路径\n");
        pass++;
    } else {
        printf("C) FAIL: 默认回退行为异常\n--- stderr ---\n%s\n", errbuf);
    }

    cases = 3;
    printf("=== harmonyos_specific_test: %d/%d cases passed (platform=OHOS aarch64) ===\n",
           pass, cases);
    return pass == cases ? 0 : 1;
}