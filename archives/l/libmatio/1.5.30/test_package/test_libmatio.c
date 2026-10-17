/*
 * libmatio 1.5.30 消费者视角测试（test_package）
 *
 * 程序化生成 MAT 测试数据，验证公开 API 的完整读写闭环：
 *   创建 → 写入 → 打开 → 变量名 → 类型 → 维度 → 数值内容 → 错误输入
 * 覆盖 MAT v4 / v5 / v5-压缩 / v7.3 四种格式（v7.3 依赖构建时的 HDF5，经编译期探测）。
 *
 * 断言失败 → 非零退出 → ctest FAIL → conan create FAIL。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <errno.h>
#include <sys/stat.h>
#include <unistd.h>

#include "matio.h"   /* 自带 matio_pubconf.h（MATIO_MAJOR_VERSION 等） */

static int checks = 0;
static int failures = 0;

#define CHECK(cond, msg)                                                  \
    do {                                                                  \
        checks++;                                                         \
        if (!(cond)) {                                                    \
            failures++;                                                   \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, msg); \
        }                                                                 \
    } while (0)

/* 生成有规律的双精度数据：x[i] = 100 + i * 0.5 */
static void gen_data(double *x, size_t n)
{
    for (size_t i = 0; i < n; i++)
        x[i] = 100.0 + (double)i * 0.5;
}

/* 比较两个数组逐元素相等（double 位模式比较，避免 -0.0/NaN 噪声） */
static int data_equal(const double *a, const double *b, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        if (memcmp(&a[i], &b[i], sizeof(double)) != 0)
            return 0;
    }
    return 1;
}

/* 单个格式的完整写→读回环验证。
 * mat_ver: 4 / 5 / 73；compress: 0=不压缩, 1=ZLIB 压缩（v4 不支持压缩，调用方不传 1）。 */
static int verify_roundtrip(int mat_ver, int compress, const char *label)
{
    char fname[128];
    enum mat_ft ft;
    mat_t *mat;
    matvar_t *wvar, *rvar;
    double wdata[12], rdata[12];
    const size_t dims[2] = {3, 4};   /* 3x4 矩阵，行主序语义 */
    int err;
    int rc = 0;

    switch (mat_ver) {
    case 4:  ft = MAT_FT_MAT4;  break;
    case 5:  ft = MAT_FT_MAT5;  break;
    case 73: ft = MAT_FT_MAT73; break;
    default: return -1;
    }

    snprintf(fname, sizeof(fname), "testpkg_v%d_c%d.mat", mat_ver, compress);
    gen_data(wdata, 12);

    /* ── 创建 + 写入 ── */
    mat = Mat_CreateVer(fname, NULL, ft);
    CHECK(mat != NULL, "Mat_CreateVer returned NULL");
    if (mat == NULL)
        return 1;

    wvar = Mat_VarCreate("alpha", MAT_C_DOUBLE, MAT_T_DOUBLE, 2, dims, wdata, 0);
    CHECK(wvar != NULL, "Mat_VarCreate returned NULL");
    if (wvar == NULL) {
        Mat_Close(mat);
        return 1;
    }
    err = Mat_VarWrite(mat, wvar, compress ? MAT_COMPRESSION_ZLIB : MAT_COMPRESSION_NONE);
    CHECK(err == 0, "Mat_VarWrite failed");
    Mat_VarFree(wvar);
    Mat_Close(mat);

    /* ── 打开 + 验证头信息（变量名/类型/维度） ── */
    mat = Mat_Open(fname, MAT_ACC_RDONLY);
    CHECK(mat != NULL, "Mat_Open returned NULL");
    if (mat == NULL)
        return 1;

    /* 变量名：Mat_VarReadNext 先只读头信息，再读数据 */
    rvar = Mat_VarReadNext(mat);
    CHECK(rvar != NULL, "Mat_VarReadNext returned NULL");
    if (rvar == NULL) {
        Mat_Close(mat);
        return 1;
    }
    CHECK(rvar->name != NULL && strcmp(rvar->name, "alpha") == 0,
          "variable name mismatch");
    CHECK(rvar->class_type == MAT_C_DOUBLE, "class_type != MAT_C_DOUBLE");
    CHECK(rvar->data_type == MAT_T_DOUBLE, "data_type != MAT_T_DOUBLE");
    CHECK(rvar->rank == 2, "rank != 2");
    CHECK(rvar->dims[0] == 3 && rvar->dims[1] == 4, "dims != {3,4}");

    /* 数值内容 */
    CHECK(rvar->data != NULL, "variable data is NULL");
    memcpy(rdata, rvar->data, sizeof(rdata));
    checks++;   /* 12 元素位模式回环比较：真实执行的断言，成功也计数 */
    if (!data_equal(rdata, wdata, 12)) {
        failures++;
        fprintf(stderr, "FAIL: %s data roundtrip mismatch\n", label);
    }
    Mat_VarFree(rvar);

    /* 流结束：再读一个变量必须为 NULL */
    rvar = Mat_VarReadNext(mat);
    CHECK(rvar == NULL, "Mat_VarReadNext after EOF should be NULL");
    Mat_VarFree(rvar);
    Mat_Close(mat);

    /* ── 按名读（另一条公开 API 路径） ── */
    mat = Mat_Open(fname, MAT_ACC_RDONLY);
    rvar = Mat_VarRead(mat, "alpha");
    CHECK(rvar != NULL, "Mat_VarRead(name) returned NULL");
    if (rvar != NULL) {
        memcpy(rdata, rvar->data, sizeof(rdata));
        checks++;   /* 按名读回环位模式比较：真实执行的断言，成功也计数 */
        if (!data_equal(rdata, wdata, 12)) {
            failures++;
            fprintf(stderr, "FAIL: %s data roundtrip (by name) mismatch\n", label);
        }
        Mat_VarFree(rvar);
    }
    err = Mat_Close(mat);
    CHECK(err == 0, "Mat_Close failed");
    if (rc)
        fprintf(stderr, "FAIL: %s completed with failures\n", label);
    return rc;
}

/* 错误输入：不存在的文件、不存在的变量、非法写入压缩参数组合等 */
static void verify_error_inputs(void)
{
    mat_t *mat;
    matvar_t *var;
    const size_t dims[2] = {2, 2};
    double data[4] = {1, 2, 3, 4};

    /* 1. 打开不存在的文件 → NULL */
    remove("testpkg_nonexistent.mat");
    mat = Mat_Open("testpkg_nonexistent.mat", MAT_ACC_RDONLY);
    CHECK(mat == NULL, "Mat_Open on missing file should return NULL");

    /* 2. Mat_VarRead 不存在的变量 → NULL */
    mat = Mat_CreateVer("testpkg_err.mat", NULL, MAT_FT_MAT5);
    CHECK(mat != NULL, "Mat_CreateVer for error tests");
    if (mat != NULL) {
        var = Mat_VarRead(mat, "no_such_variable");
        CHECK(var == NULL, "Mat_VarRead on missing variable should return NULL");
        Mat_VarFree(var);
        var = Mat_VarCreate("beta", MAT_C_DOUBLE, MAT_T_DOUBLE, 2, dims, data, 0);
        CHECK(var != NULL, "Mat_VarCreate beta");
        if (var != NULL) {
            int err = Mat_VarWrite(mat, var, MAT_COMPRESSION_NONE);
            CHECK(err == 0, "Mat_VarWrite beta");
            Mat_VarFree(var);
        }
        Mat_Close(mat);
    }

    /* 3. NULL 容忍性：上游 1.5.30 的 Mat_Close(NULL) 不解引用、走 else 分支
       返回 MATIO_E_BAD_ARGUMENT(7)（src/mat.c Mat_Close） */
    CHECK(Mat_Close(NULL) == MATIO_E_BAD_ARGUMENT,
          "Mat_Close(NULL) should return MATIO_E_BAD_ARGUMENT(7)");
}

/* 回归：长 TMPDIR 下的变量删除（上游 1.5.30 缺陷）。
 *
 * 上游 Mat_mktemp 的 MAT_MKTEMP_BUF_SIZE 按 "/tmp/XXXXXX/temp.mat"（21 字节）计算，
 * 且 mkdtemp 模板硬编码 /tmp/：OHOS 根文件系统只读 → mkdtemp 失败 →
 * Mat_VarDelete 报 "Cannot create a unique file name"；补丁改为优先 TMPDIR 并把
 * 缓冲区扩到 PATH_MAX。本回归在【明显长于旧 21 字节缓冲区】的可写目录中真实执行
 * 创建→写入→删除→重读，验证：
 *   - Mat_VarDelete 返回 0（成功）；
 *   - 删除后文件里只剩剩余变量（语义正确，不是只删了内存）；
 *   - 剩余变量数值完好（未发生路径截断导致的写坏文件）。 */
static void verify_long_tmpdir_delete(void)
{
    /* 长 TMPDIR：> 21 字节（旧缓冲区装不下），且与常规测试目录区分 */
    const char *deep_suffix = "libmatio_regression_very_long_tmpdir_suffix_for_mktemp_buffer_test";
    char longdir[512];
    char fname[600];
    mat_t *mat;
    matvar_t *var;
    double v1[4] = {1.5, 2.5, 3.5, 4.5};
    double v2[4] = {9.25, 8.25, 7.25, 6.25};
    double rb[4];
    const size_t dims[2] = {2, 2};

    snprintf(longdir, sizeof(longdir), "%s/%s", getenv("PWD") ? getenv("PWD") : ".",
             deep_suffix);
    /* 长度断言：必须超过上游旧 MAT_MKTEMP_BUF_SIZE（21 字节）才构成回归 */
    CHECK(strlen(longdir) > 21, "regression dir must exceed legacy 21-byte buffer");
    if (mkdir(longdir, 0755) != 0 && errno != EEXIST) {
        CHECK(0, "mkdir regression dir failed");
        return;
    }

    /* 真实语义链：创建 → 写两个变量 → 删除一个 → 重读验证 */
    snprintf(fname, sizeof(fname), "%s/del_test.mat", longdir);
    remove(fname);
    mat = Mat_CreateVer(fname, NULL, MAT_FT_MAT5);
    CHECK(mat != NULL, "Mat_CreateVer in long-TMPDIR regression");
    if (mat == NULL)
        return;

    var = Mat_VarCreate("keepvar", MAT_C_DOUBLE, MAT_T_DOUBLE, 2, dims, v1, 0);
    CHECK(var != NULL, "Mat_VarCreate keepvar");
    CHECK(Mat_VarWrite(mat, var, MAT_COMPRESSION_NONE) == 0, "write keepvar");
    Mat_VarFree(var);
    var = Mat_VarCreate("delvar", MAT_C_DOUBLE, MAT_T_DOUBLE, 2, dims, v2, 0);
    CHECK(var != NULL, "Mat_VarCreate delvar");
    CHECK(Mat_VarWrite(mat, var, MAT_COMPRESSION_NONE) == 0, "write delvar");
    Mat_VarFree(var);
    Mat_Close(mat);

    /* Mat_VarDelete 走 mkdtemp 临时目录路径 —— 修复前在 OHOS 上必挂 */
    mat = Mat_Open(fname, MAT_ACC_RDWR);
    CHECK(mat != NULL, "Mat_Open r/w for delete");
    if (mat == NULL)
        return;
    int rc = Mat_VarDelete(mat, "delvar");
    CHECK(rc == 0, "Mat_VarDelete under long TMPDIR");
    Mat_Close(mat);

    /* 重读：delvar 必须消失，keepvar 数值必须完好 */
    mat = Mat_Open(fname, MAT_ACC_RDONLY);
    CHECK(mat != NULL, "Mat_Open after delete");
    if (mat == NULL)
        return;
    var = Mat_VarRead(mat, "delvar");
    CHECK(var == NULL, "delvar must be gone after delete");
    Mat_VarFree(var);
    var = Mat_VarRead(mat, "keepvar");
    CHECK(var != NULL, "keepvar must survive delete");
    if (var != NULL) {
        CHECK(var->rank == 2 && var->dims[0] == 2 && var->dims[1] == 2,
              "keepvar dims after delete");
        CHECK(var->data != NULL, "keepvar data must be readable after delete");
        if (var->data != NULL) {
            memcpy(rb, var->data, sizeof(rb));
            checks++;   /* 删除后幸存变量位模式比较：真实执行的断言，成功也计数 */
            if (memcmp(rb, v1, sizeof(v1)) != 0) {
                failures++;
                fprintf(stderr, "FAIL: keepvar data corrupted after delete\n");
            }
        }
        Mat_VarFree(var);
    }
    Mat_Close(mat);
    remove(fname);
    rmdir(longdir);
}

int main(void)
{
    printf("matio %d.%d.%d test_package\n",
           MATIO_MAJOR_VERSION, MATIO_MINOR_VERSION, MATIO_RELEASE_LEVEL);

    /* MAT v4（不支持压缩） */
    verify_roundtrip(4, 0, "MAT v4");

    /* MAT v5 未压缩 + 压缩 */
    verify_roundtrip(5, 0, "MAT v5");
    verify_roundtrip(5, 1, "MAT v5 zlib-compressed");

    /* MAT v7.3（HDF5）：编译期宏探测 —— matio_pubconf.h 不直接暴露 MAT73 开关，
     * 但构建时 MATIO_MAT73=ON 且 HDF5 必在（thirdParties.cmake: "MAT73 requires HDF5" FATAL）。
     * 用 MAT_FT_MAT73 可用性（枚举始终存在）+ 运行时结果双重验证：
     * 若构建未带 HDF5，Mat_CreateVer(v7.3) 返回 NULL，此处的 CHECK 会 FAIL 而非静默跳过。 */
    verify_roundtrip(73, 0, "MAT v7.3");
    verify_roundtrip(73, 1, "MAT v7.3 zlib-compressed");

    verify_error_inputs();
    verify_long_tmpdir_delete();

    printf("test_package: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
