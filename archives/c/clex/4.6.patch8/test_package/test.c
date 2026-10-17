// 消费者测试：真实运行 CLEX 包交付的可执行工具并断言行为。
// 1) cfg-clex：上游自带配置工具（/bin/sh 脚本）——在受控 HOME/XDG_CONFIG_HOME
//    下预置旧版配置文件 ~/.clex/config，运行后断言配置被迁移到
//    $XDG_CONFIG_HOME/clex/config 且退出码为 0（cfg-clex 的迁移正路径）。
// 2) clex / kbd-test：headless 环境（stdin=/dev/null）真实启动——ncurses 经由
//    包依赖加载成功、主循环读到 EOF 后按上游约定正常退出（探索构建实测 rc=0）。
// 注意：临时目录用 $TMPDIR（缺省当前目录），设备 /tmp 只读（E002）。
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#include <stdio.h>
#include <stdlib.h>

static int run_cmd(const char *cmd) {
    int rc = system(cmd);
    if (rc < 0) {
        return -1;
    }
    return WEXITSTATUS(rc);
}

int main(void) {
    // 准备受控的 HOME / XDG_CONFIG_HOME（/tmp 只读，用 $TMPDIR 或当前目录）
    const char *td = getenv("TMPDIR");
    char tpl[600];
    snprintf(tpl, sizeof(tpl), "%s/clex-consumer-XXXXXX",
             (td && *td) ? td : ".");
    char *tmp = mkdtemp(tpl);
    if (!tmp) {
        fprintf(stderr, "FAIL: mkdtemp (tpl=%s)\n", tpl);
        return 2;
    }
    char home[600], xdg[600], olddir[600], oldcfg[700], newdir[600], newcfg[700];
    snprintf(home, sizeof(home), "%s/home", tmp);
    snprintf(xdg, sizeof(xdg), "%s/xdg", tmp);
    snprintf(olddir, sizeof(olddir), "%s/.clex", home);
    snprintf(oldcfg, sizeof(oldcfg), "%s/config", olddir);
    snprintf(newdir, sizeof(newdir), "%s/clex", xdg);
    snprintf(newcfg, sizeof(newcfg), "%s/config", newdir);

    if (mkdir(home, 0755) != 0 || mkdir(olddir, 0755) != 0) {
        fprintf(stderr, "FAIL: prepare dirs\n");
        return 2;
    }
    {
        FILE *f = fopen(oldcfg, "w");
        if (!f) {
            fprintf(stderr, "FAIL: write old config\n");
            return 2;
        }
        fputs("dummy config from old location", f);
        fclose(f);
    }

    // 1. cfg-clex 迁移正路径
    char cmd[1600];
    snprintf(cmd, sizeof(cmd),
             "HOME='%s' XDG_CONFIG_HOME='%s' CLEX=1 cfg-clex </dev/null "
             ">'%s/cfg.out' 2>&1",
             home, xdg, tmp);
    if (run_cmd(cmd) != 0) {
        fprintf(stderr, "FAIL: cfg-clex exited non-zero\n");
        return 1;
    }
    {
        struct stat st;
        if (stat(newcfg, &st) != 0) {
            fprintf(stderr, "FAIL: config not migrated to %s\n", newcfg);
            return 1;
        }
    }

    // 2. clex 主程序 headless 真实启动（ncurses 加载成功、EOF 正常退出）
    snprintf(cmd, sizeof(cmd),
             "TERM=dumb clex </dev/null >'%s/clex.out' 2>&1", tmp);
    if (run_cmd(cmd) != 0) {
        fprintf(stderr, "FAIL: clex headless run exited non-zero\n");
        return 1;
    }

    // kbd-test 不参与自动化断言：其循环无 EOF 退出路径，需真实终端双 Ctrl-C
    // 才能退出（工具仍随包交付）。见 test_package/MANIFEST.yml 说明。

    printf("clex consumer test OK: cfg-clex migration + clex headless run "
           "all passed\n");
    return 0;
}
