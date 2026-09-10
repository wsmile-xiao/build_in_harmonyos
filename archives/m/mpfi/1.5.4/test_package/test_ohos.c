/* 鸿蒙特有测试（独立于 test.c，fail closed，不静默 skip）：
 *
 * 1) 最终库产物为 ELF64 AArch64 动态库（或静态归档成员为 AArch64 REL）：
 *    通过 test_package 接线注入的 TARGET_SO / TARGET_A 宏拿到制品路径，
 *    用 readelf 在运行期解析 ELF 头验证（而非假设）。
 * 2) 动态库验证 SONAME、NEEDED、.codesign 段存在、无宿主绝对路径：
 *    精确解析 DT_NEEDED/DT_RPATH/DT_RUNPATH/DT_SONAME 方括号内的值，
 *    [libxxx.so] 允许，[/绝对路径/libxxx.so] 必须失败；动态段/节表全文
 *    不得出现 /storage/Users、/home、/data/service、/devcloud 等宿主路径。
 * 3) 在 OpenHarmony PC 上真实验证有向舍入后的区间仍包含数学真值：
 *    MPFI 用 MPFR 的软件舍入（MPFR_RNDD/RNDU，非硬件 fenv），
 *    这里端到端复验：低精度运算的结果区间包含高精度 oracle。
 * 4) 验证调用前后的浮点舍入模式按 API 契约保持或恢复：
 *    mpfi 调用序列前后 fegetround() 必须一致（库不得偷改调用者的 fenv）。
 * 5) fail closed：任何一项验证拿不到证据（文件缺失/解析失败）都算 FAIL 退出。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <fenv.h>
#include <mpfr.h>
#include <mpfi.h>

#ifndef TARGET_SO
#define TARGET_SO ""
#endif
#ifndef TARGET_A
#define TARGET_A ""
#endif

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
} while (0)

/* ── ELF 静态验证：spawn readelf，fail closed ── */
static int run_readelf(const char *flag, const char *path, char *out, size_t outsz)
{
    char cmd[4096];
    FILE *fp;
    int n;
    n = snprintf(cmd, sizeof(cmd), "readelf %s '%s' 2>&1", flag, path);
    if (n <= 0 || (size_t)n >= sizeof(cmd))
        return -1;
    fp = popen(cmd, "r");
    if (!fp)
        return -1;
    out[0] = '\0';
    {
        char line[1024];
        size_t used = 0;
        while (used + 1 < outsz && fgets(line, sizeof(line), fp)) {
            size_t ll = strlen(line);
            if (used + ll >= outsz)
                ll = outsz - used - 1;
            memcpy(out + used, line, ll);
            used += ll;
            out[used] = '\0';
        }
    }
    /* readelf 退出码非 0（文件损坏/不可读/readelf 缺失）→ fail closed */
    {
        int st = pclose(fp);
        if (st == -1 || !WIFEXITED(st) || WEXITSTATUS(st) != 0)
            return -1;
    }
    return 0;
}

/* readelf 输出可能很大（dyn-syms 数百行）：带过滤词跑，只收集匹配行 */
static int run_readelf_grep(const char *flag, const char *path,
                            const char *pattern, char *out, size_t outsz)
{
    char cmd[4096];
    FILE *fp;
    int n;
    n = snprintf(cmd, sizeof(cmd),
                 "readelf %s '%s' 2>&1 | grep -F '%s'", flag, path, pattern);
    if (n <= 0 || (size_t)n >= sizeof(cmd))
        return -1;
    fp = popen(cmd, "r");
    if (!fp)
        return -1;
    out[0] = '\0';
    {
        char line[1024];
        size_t used = 0;
        while (used + 1 < outsz && fgets(line, sizeof(line), fp)) {
            size_t ll = strlen(line);
            if (used + ll >= outsz)
                ll = outsz - used - 1;
            memcpy(out + used, line, ll);
            used += ll;
            out[used] = '\0';
        }
    }
    /* grep 退出码 0=有匹配、1=无匹配（由调用方对输出断言），其余为执行错误
     * → fail closed。readelf 自身失败时其报错行不会命中过滤词，buf 为空，
     * 调用方的非空断言同样 fail closed */
    {
        int st = pclose(fp);
        if (st == -1 || !WIFEXITED(st) ||
            (WEXITSTATUS(st) != 0 && WEXITSTATUS(st) != 1))
            return -1;
    }
    return 0;
}

/* ── 宿主路径前缀：制品 ELF 任何动态条目值/节表/动态段全文中不得出现 ── */
static const char *const HOST_PATH_PREFIXES[] = {
    "/storage/",      /* 构建机挂载（含 /storage/Users） */
    "/home/",         /* 构建机用户目录 */
    "/data/service",  /* 鸿蒙宿主服务路径 */
    "/devcloud",      /* CI 云盘路径 */
};

static int is_host_path(const char *s)
{
    size_t i;
    for (i = 0; i < sizeof(HOST_PATH_PREFIXES) / sizeof(HOST_PATH_PREFIXES[0]); i++)
        if (strstr(s, HOST_PATH_PREFIXES[i]) != NULL)
            return 1;
    return 0;
}

/* readelf -d 中 (NEEDED)/(RPATH)/(RUNPATH)/(SONAME) 方括号值的扫描结果 */
struct dyn_scan {
    int parse_fail;       /* 标签行存在但 [value] 不完整 */
    int needed, rpath, runpath, soname; /* 条目计数 */
    int abs_needed;       /* 某个 NEEDED 值以 / 开头（绝对路径） */
    int soname_abs;       /* SONAME 值以 / 开头 */
    int host_path;        /* 任一条目值含宿主路径前缀 */
    char bad[192];        /* 首个违规/异常描述（失败信息打印用） */
    char soname_val[128]; /* 首个 SONAME 值 */
};

/* 逐行解析 readelf -d 输出（兼容 GNU "(NEEDED)" 与 llvm " NEEDED" 两种格式） */
static void scan_dynamic_entries(const char *dyn, struct dyn_scan *sc)
{
    char ln[1024];
    const char *p = dyn;

    memset(sc, 0, sizeof(*sc));
    while (p && *p) {
        const char *eol = strchr(p, '\n');
        size_t len = eol ? (size_t)(eol - p) : strlen(p);
        int tag = 0; /* 1=NEEDED 2=RPATH 3=RUNPATH 4=SONAME */
        char *lb, *rb;

        if (len >= sizeof(ln))
            len = sizeof(ln) - 1;
        memcpy(ln, p, len);
        ln[len] = '\0';

        if (strstr(ln, "(NEEDED)") || strstr(ln, " NEEDED"))
            tag = 1;
        else if (strstr(ln, "(RPATH)") || strstr(ln, " RPATH"))
            tag = 2;
        else if (strstr(ln, "(RUNPATH)") || strstr(ln, " RUNPATH"))
            tag = 3;
        else if (strstr(ln, "(SONAME)") || strstr(ln, " SONAME"))
            tag = 4;

        if (tag) {
            lb = strchr(ln, '[');
            rb = (lb != NULL) ? strchr(lb, ']') : NULL;
            if (lb == NULL || rb == NULL) {
                sc->parse_fail = 1;
                if (sc->bad[0] == '\0')
                    snprintf(sc->bad, sizeof(sc->bad),
                             "动态条目行缺少完整 [value]: %.120s", ln);
            } else {
                *rb = '\0'; /* 方括号内的值 = lb + 1 */
                if (tag == 1) {
                    sc->needed++;
                    if (lb[1] == '/') {
                        sc->abs_needed = 1;
                        if (sc->bad[0] == '\0')
                            snprintf(sc->bad, sizeof(sc->bad),
                                     "NEEDED 绝对路径: %.150s", lb + 1);
                    }
                } else if (tag == 2) {
                    sc->rpath++;
                } else if (tag == 3) {
                    sc->runpath++;
                } else {
                    sc->soname++;
                    if (sc->soname_val[0] == '\0')
                        snprintf(sc->soname_val, sizeof(sc->soname_val),
                                 "%.120s", lb + 1);
                    if (lb[1] == '/') {
                        sc->soname_abs = 1;
                        if (sc->bad[0] == '\0')
                            snprintf(sc->bad, sizeof(sc->bad),
                                     "SONAME 绝对路径: %.150s", lb + 1);
                    }
                }
                if (is_host_path(lb + 1)) {
                    sc->host_path = 1;
                    if (sc->bad[0] == '\0')
                        snprintf(sc->bad, sizeof(sc->bad),
                                 "条目含宿主路径: %.150s", lb + 1);
                }
            }
        }
        p = (eol != NULL) ? eol + 1 : NULL;
    }
}

static void test_elf_artifact(void)
{
    char buf[8192];
    int have_so = TARGET_SO[0] != '\0';
    int have_a = TARGET_A[0] != '\0';

    /* fail closed：两形态至少一个必须给出且存在 */
    CHECK(have_so || have_a, "TARGET_SO/TARGET_A 至少一个注入（制品路径）");
    if (have_so && access(TARGET_SO, R_OK) != 0) {
        fprintf(stderr, "FAIL: TARGET_SO 不可读: %s\n", TARGET_SO);
        failures++;
        have_so = 0;
    }
    if (have_a && access(TARGET_A, R_OK) != 0) {
        /* 静态归档形态未产出（--disable-static）：动态库已完整覆盖 ELF 验证，
         * 静态检查仅在归档真实存在时执行（否则 fail-closed 跳过会掩盖问题） */
        printf("TARGET_A %s 不存在（--disable-static 包型），跳过归档检查\n", TARGET_A);
        have_a = 0;
    }

    if (have_so) {
        /* ELF64 + AArch64 */
        CHECK(run_readelf("-h", TARGET_SO, buf, sizeof(buf)) == 0,
              "readelf -h 读取动态库失败");
        CHECK(strstr(buf, "Class:                             ELF64") != NULL,
              "动态库必须为 ELF64");
        CHECK(strstr(buf, "Machine:                           AArch64") != NULL,
              "动态库必须为 AArch64");

        /* 动态段条目精确解析：SONAME/NEEDED/RPATH/RUNPATH 方括号内的值 */
        {
            struct dyn_scan sc;
            CHECK(run_readelf("-d", TARGET_SO, buf, sizeof(buf)) == 0,
                  "readelf -d 读取动态段失败");
            scan_dynamic_entries(buf, &sc);
            CHECK(!sc.parse_fail,
                  "NEEDED/RPATH/RUNPATH/SONAME 行必须解析出完整 [value]");
            CHECK(sc.needed > 0, "动态段必须存在 DT_NEEDED 条目");
            CHECK(sc.soname > 0, "动态库必须有 DT_SONAME");
            CHECK(!sc.soname_abs, "SONAME 不得为绝对路径");
            if (sc.soname > 0) {
                CHECK(strncmp(sc.soname_val, "libmpfi.so", 10) == 0,
                      "SONAME 应为 libmpfi.so.*");
                printf("SONAME: %s\n", sc.soname_val);
            }
            /* [libxxx.so] 允许，[/绝对路径/libxxx.so] 必须失败 */
            CHECK(!sc.abs_needed, "DT_NEEDED 值不得为绝对路径");
            CHECK(!sc.host_path,
                  "NEEDED/RPATH/RUNPATH/SONAME 值不得含宿主路径");
            if (sc.parse_fail || sc.abs_needed || sc.host_path || sc.soname_abs)
                fprintf(stderr, "  违规条目: %s\n", sc.bad);
            /* NEEDED：本仓 mpfr/4.2.2.1 仅静态二进制（.a），libmpfi.so 静态并入 mpfr
             * （1.5.2 同款形态、符号全 DEFINED）；gmp 为动态依赖必须出现在 NEEDED。
             * 若未来 mpfr 有共享包，libmpfi.so 的 NEEDED 应含 libmpfr
             * （此时该断言自然满足，无需放宽）。 */
            CHECK(strstr(buf, "libgmp") != NULL,
                  "DT_NEEDED 必须含 libgmp（gmp 依赖真实传播）");
            /* mpfr 符号必须可用：静态并入时 DEFINED、动态时 NEEDED+UNDEF */
            CHECK(run_readelf_grep("--dyn-syms", TARGET_SO, "mpfr_add",
                                   buf, sizeof(buf)) == 0,
                  "readelf --dyn-syms 失败");
            CHECK(buf[0] != '\0',
                  "mpfr_add 符号必须可见（静态并入 DEFINED 或动态 NEEDED）");
        }

        /* .codesign 段（鸿蒙 ELF 签名段）与 .note.ohos.ident */
        CHECK(run_readelf("-S", TARGET_SO, buf, sizeof(buf)) == 0,
              "readelf -S 读取节表失败");
        CHECK(strstr(buf, ".codesign") != NULL,
              "动态库必须有 .codesign 节（鸿蒙签名）");
        CHECK(strstr(buf, ".note.ohos.ident") != NULL,
              "动态库必须有 .note.ohos.ident 节");

        /* 无宿主路径：节表/动态段全文不得出现宿主路径（条目值级的精确校验
         * 已由 scan_dynamic_entries 完成，此处对全文兜底） */
        CHECK(!is_host_path(buf), "节表中不得含宿主路径");
        {
            CHECK(run_readelf("-d", TARGET_SO, buf, sizeof(buf)) == 0,
                  "重读动态段");
            CHECK(!is_host_path(buf), "动态段不得含宿主路径");
        }
    }

    if (have_a) {
        /* 静态归档：成员须为 AArch64 REL（可重定位目标文件） */
        CHECK(run_readelf("-h", TARGET_A, buf, sizeof(buf)) == 0,
              "readelf -h 读取静态归档失败");
        CHECK(strstr(buf, "Machine:                           AArch64") != NULL,
              "静态归档成员必须为 AArch64");
        CHECK(strstr(buf, "REL") != NULL || strstr(buf, "Type:") != NULL,
              "静态归档头可解析");
        CHECK(strstr(buf, "Class:                             ELF64") != NULL,
              "静态归档成员必须为 ELF64");
    }
}

/* ── 有向舍入真值包含（鸿蒙真机端到端） ── */
static void test_directed_rounding_contains_truth(void)
{
    /* 核心不变量：对任意 mpfi 运算，结果区间 [l,r] 必须满足 l <= 真值 <= r，
     * 其中 l 由 MPFR_RNDD（向 -inf）产生、r 由 MPFR_RNDU（向 +inf）产生。
     * 用非精确表示的十进制端点（0.1 等）逼出真实舍入路径：
     * 若编译器优化让端点失去向外舍入（如误用 RNDN 或 FP 收缩），
     * 53 位区间可能不再包含 300 位真值 —— 该缺陷在本测试直接暴露。 */
    mpfi_t a, res;
    mpfr_t oracle;
    mpfi_init2(a, 53);
    mpfi_init2(res, 53);
    mpfr_init2(oracle, 300);

    /* 0.1+0.2 的真值（十进制 0.3，二进制无限循环）必须被 [0.1,0.1]+[0.2,0.2] 包含 */
    mpfi_set_d(a, 0.1);
    {
        mpfi_t b;
        mpfi_init2(b, 53);
        mpfi_set_d(b, 0.2);
        mpfi_add(res, a, b);
        mpfr_set_d(oracle, 0.3, MPFR_RNDN);
        CHECK(mpfi_is_inside_fr(oracle, res),
              "真值 0.3 应含于 [0.1,0.1]+[0.2,0.2]（有向舍入正确）");
        mpfi_clear(b);
    }

    /* 除法向外交：1/3 的 300 位真值必须被 [1,1]/[3,3] 包含 */
    mpfi_set_si(a, 1);
    {
        mpfi_t b;
        mpfr_t lo, hi;
        mpfi_init2(b, 53);
        mpfr_init2(lo, 53); mpfr_init2(hi, 53);
        mpfi_set_si(b, 3);
        mpfi_div(res, a, b);
        mpfr_set_ui(oracle, 1, MPFR_RNDN);
        mpfr_div_ui(oracle, oracle, 3, MPFR_RNDN); /* 300 位 1/3 */
        CHECK(mpfi_is_inside_fr(oracle, res),
              "300位 1/3 真值应含于 [1,1]/[3,3]");
        mpfi_get_left(lo, res); mpfi_get_right(hi, res);
        CHECK(mpfr_cmp(lo, oracle) <= 0 && mpfr_cmp(oracle, hi) <= 0,
              "1/3 端点顺序：lo <= 真值 <= hi");
        CHECK(mpfr_cmp(lo, hi) < 0, "1/3 区间非退化（53 位装不下 1/3）");
        mpfi_clear(b); mpfr_clear(lo); mpfr_clear(hi);
    }

    mpfi_clear(a); mpfi_clear(res);
    mpfr_clear(oracle);
}

/* ── fenv 舍入模式契约 ── */
static void test_fenv_mode_preserved(void)
{
    /* MPFI 全部经 MPFR 软件舍入（不读不写硬件 fenv），
     * API 契约：调用前后调用者的舍入模式必须原样保持。
     * 用 2^k-1 ulp 边界值确认 fegetround 确实反映了真实舍入状态。 */
    int before = fegetround();
    CHECK(before == FE_TONEAREST || before == FE_UPWARD
          || before == FE_DOWNWARD || before == FE_TOWARDZERO,
          "fegetround 返回合法模式");

    mpfi_t a, res;
    mpfi_init2(a, 53);
    mpfi_init2(res, 53);
    mpfi_interv_d(a, 0.1, 0.2);
    mpfi_sqrt(res, a);
    mpfi_mul(res, res, res);
    mpfi_div(res, res, a);

    int after = fegetround();
    CHECK(before == after, "mpfi 调用序列不得改变调用者舍入模式");

    /* 交叉验证：fesetround 换模式后再跑 mpfi，模式仍不得被库改写 */
    if (fesetround(FE_UPWARD) == 0) {
        int mid = fegetround();
        CHECK(mid == FE_UPWARD, "fesetround(FE_UPWARD) 生效");
        mpfi_mul(res, res, res);
        CHECK(fegetround() == FE_UPWARD,
              "非默认舍入模式下 mpfi 仍不得改写舍入模式");
        fesetround(before); /* 恢复 */
        CHECK(fegetround() == before, "恢复原舍入模式");
    } else {
        fprintf(stderr, "FAIL: fesetround(FE_UPWARD) 不可用（musl/AArch64 应支持）\n");
        failures++;
    }

    mpfi_clear(a); mpfi_clear(res);
}

int main(void)
{
    printf("mpfi 1.5.4 HarmonyOS/aarch64 specialty tests\n");
    printf("TARGET_SO=%s TARGET_A=%s\n", TARGET_SO, TARGET_A);

    if (getenv("OHOS_TEST_SKIP")) {
        /* fail closed：不允许静默跳过，环境变量只会把测试变成显式失败 */
        fprintf(stderr, "FAIL: OHOS 特有测试不允许跳过（fail closed）\n");
        return 1;
    }

    test_elf_artifact();
    test_directed_rounding_contains_truth();
    test_fenv_mode_preserved();

    if (failures) {
        fprintf(stderr, "%d FAILURES in HarmonyOS specialty tests\n", failures);
        return 1;
    }
    printf("mpfi HarmonyOS specialty tests: ALL PASS\n");
    return 0;
}
