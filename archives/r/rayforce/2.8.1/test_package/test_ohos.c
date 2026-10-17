/*
 * HarmonyOS 专项测试 — rayforce 2.8.1 on OHOS (aarch64).
 *
 * 真实可执行的鸿蒙专项用例: 仅使用公开头文件 <rayforce.h> 与静态库,
 * 在 OHOS 平台验证引擎的数据通路(向量/表/空值/字典 API)的可观测结果。
 * 与上游 test_*.c 不同 — 本用例独立于上游测试框架, 由本配方自带并实际运行。
 */
#include <rayforce.h>
#include <stdio.h>
#include <string.h>

static int fail(const char* what) {
    fprintf(stderr, "OHOS-SPECIAL FAIL: %s\n", what);
    return 1;
}

int main(void) {
    (void)ray_sym_init();

    /* 1. 版本探针: ray_version_string() 必须报告 2.8.1 */
    {
        const char* vs = ray_version_string();
        if (!vs) return fail("ray_version_string NULL");
        if (strncmp(vs, "2.8.1", 5) != 0) {
            fprintf(stderr, "OHOS-SPECIAL version=%s\n", vs);
            return fail("version mismatch");
        }
    }

    /* 2. 向量通路: 构造/追加/取数/置空 (可观测结果) */
    {
        int64_t raw[] = {10, 20, 30};
        ray_t* v = ray_vec_from_raw(RAY_I64, raw, 3);
        if (!v || RAY_IS_ERR(v)) return fail("ray_vec_from_raw");
        int64_t x = 40;
        v = ray_vec_append(v, &x);
        if (RAY_IS_ERR(v)) return fail("ray_vec_append");
        if (ray_vec_get_i64(v, 0) != 10 || ray_vec_get_i64(v, 3) != 40)
            return fail("ray_vec_get_i64");
        if (ray_vec_set_null_checked(v, 1, true) != RAY_OK) return fail("set null");
        if (!ray_vec_is_null(v, 1) || ray_vec_is_null(v, 0)) return fail("null flags");
        /* 空值槽位数值为 NULL_I64 */
        if (ray_vec_get_i64(v, 1) != NULL_I64) return fail("NULL_I64 slot");
        ray_release(v);
    }

    /* 3. 表通路: 命名列 + 行数 */
    {
        int64_t vals[] = {5, 6, 7};
        ray_t* col = ray_vec_from_raw(RAY_I64, vals, 3);
        if (!col || RAY_IS_ERR(col)) return fail("vec col");
        ray_t* tbl = ray_table_new(1);
        if (!tbl || RAY_IS_ERR(tbl)) return fail("ray_table_new");
        int64_t name = ray_sym_intern("x", 1);
        tbl = ray_table_add_col(tbl, name, col);
        if (RAY_IS_ERR(tbl)) return fail("ray_table_add_col");
        if (ray_table_nrows(tbl) != 3) return fail("ray_table_nrows");
        ray_release(tbl);
    }

    /* 4. 字典通路: upsert/get 可观测语义 */
    {
        const char* kptrs[] = {"k"};
        const uint32_t klens[] = {1};
        int64_t v0 = 0;
        ray_t* keys = ray_str_vec_from_parts(kptrs, klens, NULL, 1);
        ray_t* vals = ray_vec_from_raw(RAY_I64, &v0, 1);
        ray_t* dict = ray_dict_new(keys, vals);
        if (!dict || RAY_IS_ERR(dict)) return fail("ray_dict_new");
        dict = ray_dict_upsert(dict, ray_str("k", 1), ray_i64(1234));
        if (!dict || RAY_IS_ERR(dict)) return fail("ray_dict_upsert");
        ray_t* got = ray_dict_get(dict, ray_str("k", 1));
        if (!got || RAY_IS_ERR(got)) return fail("ray_dict_get");
        if (got->type != -RAY_I64 || got->i64 != 1234) return fail("dict value");
        ray_release(got);
        ray_release(dict);
    }

    printf("rayforce OHOS-SPECIAL test: PASS (rayforce %s)\n", ray_version_string());
    return 0;
}