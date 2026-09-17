/*
 * test_libmsym.c — libmsym 消费者功能测试（鸿蒙 PC 侧新增）
 *
 * 上游 v0.2.3 没有任何测试入口：源码树只有 src/ 与 examples/，顶层 CMakeLists.txt
 * 无 enable_testing()/CTest，仓库无 test/ 目录。因此这里从**消费者视角**补测：
 * 链接交付出来的 libmsym，对已知点群的标准分子几何做判定断言。
 *
 * 期望值来自分子点群理论（独立于本库实现），不是从本库输出反推：
 *   H2O  -> C2v, order 4  = E + C2 + 2σv
 *   NH3  -> C3v, order 6  = E + 2C3 + 3σv
 *   CH4  -> Td , order 24 = E + 8C3 + 3C2 + 6S4 + 6σd
 *   C6H6 -> D6h, order 24 = E + 2C6 + 2C3 + C2 + 3C2' + 3C2'' + i + 2S3 + 2S6 + σh + 3σv + 3σd
 * 特征标表不可约表示数：C2v=4, C3v=3, Td=5, D6h=12。
 */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <libmsym/msym.h>

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, ...)                                                      \
    do {                                                                      \
        if (cond) {                                                           \
            g_pass++;                                                         \
        } else {                                                              \
            g_fail++;                                                         \
            printf("FAIL %s:%d: ", __FILE__, __LINE__);                       \
            printf(__VA_ARGS__);                                              \
            printf("\n");                                                     \
        }                                                                     \
    } while (0)

#define MAX_ATOMS 12

typedef struct {
    const char *label;
    int atom_count;
    const char *names[MAX_ATOMS];
    double xyz[MAX_ATOMS][3];
    msym_point_group_type_t type;
    int type_n;               /* msymGetPointGroupType 的 n = 主转动阶数（Td 的主转动是 C3 → 3） */
    const char *pg_name;      /* msymGetPointGroupName */
    int order;                /* 对称操作总数 */
    int n_proper;             /* PROPER_ROTATION（不含 E） */
    int n_improper;           /* IMPROPER_ROTATION（不含 i） */
    int n_reflection;         /* REFLECTION */
    int n_inversion;          /* INVERSION */
    int char_table_d;         /* 不可约表示个数 */
    int n_eq_sets;            /* 等价集个数 */
    int eq_len_a, eq_len_b;   /* 等价集长度（升序） */
} mol_t;

/* 水：O-H 0.9575 Å，H-O-H 104.5°，C2 轴沿 +y */
static const mol_t MOL_WATER = {
    "H2O", 3,
    {"O", "H", "H"},
    {{0.0, 0.0, 0.0}, {0.7571, 0.5861, 0.0}, {-0.7571, 0.5861, 0.0}},
    MSYM_POINT_GROUP_TYPE_Cnv, 2, "C2v",
    4, 1, 0, 2, 0, 4, 2, 1, 2
};

/* 氨：N-H 1.0124 Å，H-N-H 106.7°，C3 轴沿 +z */
static const mol_t MOL_AMMONIA = {
    "NH3", 4,
    {"N", "H", "H", "H"},
    {{0.0, 0.0, 0.1173},
     {0.0, 0.9397, -0.2736},
     {0.8138, -0.4698, -0.2736},
     {-0.8138, -0.4698, -0.2736}},
    MSYM_POINT_GROUP_TYPE_Cnv, 3, "C3v",
    6, 2, 0, 3, 0, 3, 2, 1, 3
};

/* 甲烷：C-H 1.089 Å，正四面体（主转动为 C3，故 n=3） */
static const mol_t MOL_METHANE = {
    "CH4", 5,
    {"C", "H", "H", "H", "H"},
    {{0.0, 0.0, 0.0},
     {0.6291, 0.6291, 0.6291},
     {0.6291, -0.6291, -0.6291},
     {-0.6291, 0.6291, -0.6291},
     {-0.6291, -0.6291, 0.6291}},
    MSYM_POINT_GROUP_TYPE_Td, 3, "Td",
    24, 11, 6, 6, 0, 5, 2, 1, 4
};

/* 苯：C-C 1.397 Å，C-H 1.084 Å，平面 D6h */
static const mol_t MOL_BENZENE = {
    "C6H6", 12,
    {"C", "C", "C", "C", "C", "C", "H", "H", "H", "H", "H", "H"},
    {{1.3970, 0.0000, 0.0},
     {0.6985, 1.2098, 0.0},
     {-0.6985, 1.2098, 0.0},
     {-1.3970, 0.0000, 0.0},
     {-0.6985, -1.2098, 0.0},
     {0.6985, -1.2098, 0.0},
     {2.4810, 0.0000, 0.0},
     {1.2405, 2.1486, 0.0},
     {-1.2405, 2.1486, 0.0},
     {-2.4810, 0.0000, 0.0},
     {-1.2405, -2.1486, 0.0},
     {1.2405, -2.1486, 0.0}},
    MSYM_POINT_GROUP_TYPE_Dnh, 6, "D6h",
    24, 11, 4, 7, 1, 12, 2, 6, 6
};

static void fill_element(msym_element_t *e, const char *name, const double v[3])
{
    memset(e, 0, sizeof(*e));
    snprintf(e->name, sizeof(e->name), "%s", name);
    e->v[0] = v[0];
    e->v[1] = v[1];
    e->v[2] = v[2];
}

static void run_mol(const mol_t *m)
{
    msym_element_t elements[MAX_ATOMS];
    msym_context ctx;
    msym_point_group_type_t type = MSYM_POINT_GROUP_TYPE_Kh;
    const msym_symmetry_operation_t *sops = NULL;
    const msym_character_table_t *ct = NULL;
    const msym_equivalence_set_t *es = NULL;
    const msym_subgroup_t *sg = NULL;
    const msym_thresholds_t *th = NULL;
    char name[8];
    double radius = 0.0;
    int i, sopsl = 0, esl = 0, sgl = 0, n = -1;
    int c_ident = 0, c_proper = 0, c_improper = 0, c_refl = 0, c_inv = 0;

    for (i = 0; i < m->atom_count; i++)
        fill_element(&elements[i], m->names[i], m->xyz[i]);

    ctx = msymCreateContext();
    CHECK(ctx != NULL, "[%s] msymCreateContext 返回非空", m->label);
    if (ctx == NULL)
        return;

    CHECK(msymSetElements(ctx, m->atom_count, elements) == MSYM_SUCCESS,
          "[%s] msymSetElements(%d) 失败", m->label, m->atom_count);
    CHECK(msymFindSymmetry(ctx) == MSYM_SUCCESS,
          "[%s] msymFindSymmetry 失败", m->label);

    CHECK(msymGetPointGroupType(ctx, &type, &n) == MSYM_SUCCESS,
          "[%s] msymGetPointGroupType 失败", m->label);
    CHECK(type == m->type && n == m->type_n,
          "[%s] 点群类型/轴阶数 = %d/%d，期望 %d/%d",
          m->label, (int)type, n, (int)m->type, m->type_n);

    memset(name, 0, sizeof(name));
    CHECK(msymGetPointGroupName(ctx, sizeof(name), name) == MSYM_SUCCESS,
          "[%s] msymGetPointGroupName 失败", m->label);
    CHECK(strcmp(name, m->pg_name) == 0,
          "[%s] 点群名 = '%s'，期望 '%s'", m->label, name, m->pg_name);

    CHECK(msymGetSymmetryOperations(ctx, &sopsl, &sops) == MSYM_SUCCESS
              && sops != NULL,
          "[%s] msymGetSymmetryOperations 失败", m->label);
    CHECK(sopsl == m->order,
          "[%s] 对称操作数 = %d，期望群阶 %d", m->label, sopsl, m->order);

    for (i = 0; i < sopsl; i++) {
        switch (sops[i].type) {
        case MSYM_SYMMETRY_OPERATION_TYPE_IDENTITY: c_ident++; break;
        case MSYM_SYMMETRY_OPERATION_TYPE_PROPER_ROTATION: c_proper++; break;
        case MSYM_SYMMETRY_OPERATION_TYPE_IMPROPER_ROTATION: c_improper++; break;
        case MSYM_SYMMETRY_OPERATION_TYPE_REFLECTION: c_refl++; break;
        case MSYM_SYMMETRY_OPERATION_TYPE_INVERSION: c_inv++; break;
        default: break;
        }
    }
    CHECK(c_ident == 1, "[%s] 恒等操作数 = %d，期望 1", m->label, c_ident);
    CHECK(c_proper == m->n_proper,
          "[%s] 真转动数 = %d，期望 %d", m->label, c_proper, m->n_proper);
    CHECK(c_improper == m->n_improper,
          "[%s] 非真转动数 = %d，期望 %d", m->label, c_improper, m->n_improper);
    CHECK(c_refl == m->n_reflection,
          "[%s] 反映面数 = %d，期望 %d", m->label, c_refl, m->n_reflection);
    CHECK(c_inv == m->n_inversion,
          "[%s] 反演数 = %d，期望 %d", m->label, c_inv, m->n_inversion);

    CHECK(msymGetCharacterTable(ctx, &ct) == MSYM_SUCCESS && ct != NULL,
          "[%s] msymGetCharacterTable 失败", m->label);
    if (ct != NULL)
        CHECK(ct->d == m->char_table_d,
              "[%s] 不可约表示数 = %d，期望 %d",
              m->label, ct->d, m->char_table_d);

    CHECK(msymGetEquivalenceSets(ctx, &esl, &es) == MSYM_SUCCESS && es != NULL,
          "[%s] msymGetEquivalenceSets 失败", m->label);
    CHECK(esl == m->n_eq_sets,
          "[%s] 等价集个数 = %d，期望 %d", m->label, esl, m->n_eq_sets);
    if (esl == 2) {
        int a = es[0].length, b = es[1].length, t;
        if (a > b) { t = a; a = b; b = t; }
        CHECK(a == m->eq_len_a && b == m->eq_len_b,
              "[%s] 等价集长度 = {%d,%d}，期望 {%d,%d}",
              m->label, a, b, m->eq_len_a, m->eq_len_b);
    }

    CHECK(msymGetSubgroups(ctx, &sgl, &sg) == MSYM_SUCCESS && sgl > 0,
          "[%s] 子群枚举为空（sgl=%d）", m->label, sgl);

    CHECK(msymGetRadius(ctx, &radius) == MSYM_SUCCESS && radius > 0.0,
          "[%s] 分子半径 = %g，期望 > 0", m->label, radius);

    th = msymGetDefaultThresholds();
    CHECK(th != NULL, "[%s] msymGetDefaultThresholds 返回空", m->label);

    CHECK(msymReleaseContext(ctx) == MSYM_SUCCESS,
          "[%s] msymReleaseContext 失败", m->label);
}

int main(void)
{
    printf("libmsym consumer test — point group detection on standard geometries\n");
    run_mol(&MOL_WATER);
    run_mol(&MOL_AMMONIA);
    run_mol(&MOL_METHANE);
    run_mol(&MOL_BENZENE);
    printf("assertions: %d passed, %d failed\n", g_pass, g_fail);
    if (g_fail == 0) {
        printf("libmsym consumer test: ALL PASS\n");
        return 0;
    }
    printf("libmsym consumer test: FAILED\n");
    return 1;
}
