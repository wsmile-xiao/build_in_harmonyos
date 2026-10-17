/* libccd 2.1 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 算得对。这里真的跑 GJK/EPA 算法 ——
 * 形状分两种用途，这个区分很重要：
 *   · **球体**只用来验「相交/不相交」的布尔判定 —— 支撑函数对球是精确的，判定可靠。
 *   · **长方体**用来验「穿透深度」的数值 —— EPA 是在多面体上迭代逼近的算法，
 *     对球面这类曲面只能渐近收敛（实测球体 d=1.2 时算出 0.777 而解析解 0.8，
 *     差 2.3%，那是算法固有行为不是缺陷）；对多面体则是精确的，才能卡紧容差。
 *
 * 同时验证 ENABLE_DOUBLE_PRECISION=ON 真的生效：单精度下
 * 下面 1e-6 量级的容差会过不去（float 有效位约 7 位十进制）。
 */
#include <ccd/ccd.h>
#include <ccd/quat.h>
#include <ccd/vec3.h>

#include <math.h>
#include <stdio.h>

typedef struct {
    ccd_vec3_t pos;
    ccd_real_t radius;
} sphere_t;

/* 球体的支撑函数：沿 dir 方向最远的点 = 球心 + 半径 * 单位方向 */
static void sphere_support(const void *obj, const ccd_vec3_t *dir, ccd_vec3_t *v)
{
    const sphere_t *s = (const sphere_t *)obj;
    /* libccd 没有 ccdVec3Add2（三参数版）—— 只有原地相加的 ccdVec3Add。
     * 先把球心拷进 v，再加上「半径 × 单位方向」。 */
    ccd_vec3_t d;
    ccdVec3Copy(&d, dir);
    ccdVec3Normalize(&d);
    ccdVec3Scale(&d, s->radius);
    ccdVec3Copy(v, &s->pos);
    ccdVec3Add(v, &d);
}

static void sphere_center(const void *obj, ccd_vec3_t *c)
{
    ccdVec3Copy(c, &((const sphere_t *)obj)->pos);
}

typedef struct {
    ccd_vec3_t pos;   /* 中心 */
    ccd_vec3_t half;  /* 半边长 */
} box_t;

/* 长方体的支撑函数：沿 dir 每个分量取对应方向的角点 */
static void box_support(const void *obj, const ccd_vec3_t *dir, ccd_vec3_t *v)
{
    const box_t *b = (const box_t *)obj;
    ccdVec3Set(v,
        ccdVec3X(&b->pos) + (ccdVec3X(dir) >= 0 ? ccdVec3X(&b->half) : -ccdVec3X(&b->half)),
        ccdVec3Y(&b->pos) + (ccdVec3Y(dir) >= 0 ? ccdVec3Y(&b->half) : -ccdVec3Y(&b->half)),
        ccdVec3Z(&b->pos) + (ccdVec3Z(dir) >= 0 ? ccdVec3Z(&b->half) : -ccdVec3Z(&b->half)));
}

static void box_center(const void *obj, ccd_vec3_t *c)
{
    ccdVec3Copy(c, &((const box_t *)obj)->pos);
}

int main(void)
{
    ccd_t ccd;
    CCD_INIT(&ccd);
    ccd.support1 = sphere_support;
    ccd.support2 = sphere_support;
    ccd.center1  = sphere_center;
    ccd.center2  = sphere_center;
    ccd.max_iterations = 100;
    ccd.mpr_tolerance  = 1e-9;
    ccd.epa_tolerance  = 1e-9;

    sphere_t a, b;
    a.radius = 1.0; ccdVec3Set(&a.pos, 0.0, 0.0, 0.0);
    b.radius = 1.0;

    /* ① 明显相交：两球心距 1.0 < r1+r2=2.0 */
    ccdVec3Set(&b.pos, 1.0, 0.0, 0.0);
    if (!ccdGJKIntersect(&a, &b, &ccd)) {
        printf("FAIL 球心距 1.0（半径各 1.0）应判为相交，实判不相交\n");
        return 1;
    }

    /* ② 明显分离：两球心距 5.0 > 2.0 */
    ccdVec3Set(&b.pos, 5.0, 0.0, 0.0);
    if (ccdGJKIntersect(&a, &b, &ccd)) {
        printf("FAIL 球心距 5.0 应判为分离，实判相交\n");
        return 1;
    }

    /* ③ 临界外侧：2.001 应仍分离（验证判据不是粗糙的包围盒） */
    ccdVec3Set(&b.pos, 2.001, 0.0, 0.0);
    if (ccdGJKIntersect(&a, &b, &ccd)) {
        printf("FAIL 球心距 2.001 应分离，实判相交（判据过于宽松）\n");
        return 1;
    }

    /* ④ 穿透深度改用长方体（EPA 对多面体精确，可卡紧容差）。
     *    A 占 x∈[-1,1]，B 占 x∈[0.5,2.5]，y/z 完全重叠 →
     *    最小平移沿 x，深度 = 1 - 0.5 = 0.5 */
    ccd_t bccd;
    CCD_INIT(&bccd);
    bccd.support1 = box_support;
    bccd.support2 = box_support;
    bccd.center1  = box_center;
    bccd.center2  = box_center;
    bccd.max_iterations = 200;
    bccd.epa_tolerance  = 1e-10;

    box_t ba, bb;
    ccdVec3Set(&ba.pos, 0.0, 0.0, 0.0);  ccdVec3Set(&ba.half, 1.0, 1.0, 1.0);
    ccdVec3Set(&bb.pos, 1.5, 0.0, 0.0);  ccdVec3Set(&bb.half, 1.0, 1.0, 1.0);

    ccd_real_t depth = 0.0;
    ccd_vec3_t dir, pos;
    int r = ccdGJKPenetration(&ba, &bb, &bccd, &depth, &dir, &pos);
    if (r != 0) {
        printf("FAIL 长方体 ccdGJKPenetration 返回 %d（应为 0）\n", r);
        return 1;
    }
    if (fabs((double)depth - 0.5) > 1e-9) {
        printf("FAIL 长方体穿透深度 %.12f != 0.5（差 %.3e）\n",
               (double)depth, fabs((double)depth - 0.5));
        return 1;
    }

    /* ⑤ 分离方向应沿 x 轴且为单位向量 */
    {
        double len = sqrt((double)ccdVec3Len2(&dir));
        if (fabs(len - 1.0) > 1e-9) {
            printf("FAIL 分离方向不是单位向量，|dir|=%.12f\n", len);
            return 1;
        }
        if (fabs((double)ccdVec3X(&dir)) < 0.999999) {
            printf("FAIL 分离方向应沿 x 轴，|dir.x|=%.12f\n",
                   fabs((double)ccdVec3X(&dir)));
            return 1;
        }
    }

    /* ⑥ 换一组尺寸再验，防止撞巧：B 半边长 0.5、中心 x=1.2
     *    A 占 [-1,1]，B 占 [0.7,1.7] → 深度 = 1 - 0.7 = 0.3 */
    ccdVec3Set(&bb.pos, 1.2, 0.0, 0.0);  ccdVec3Set(&bb.half, 0.5, 0.5, 0.5);
    if (ccdGJKPenetration(&ba, &bb, &bccd, &depth, &dir, &pos) != 0) {
        printf("FAIL 第二组长方体未判为相交\n");
        return 1;
    }
    if (fabs((double)depth - 0.3) > 1e-9) {
        printf("FAIL 第二组穿透深度 %.12f != 0.3\n", (double)depth);
        return 1;
    }

    /* ⑦ 双精度确认：ccd_real_t 必须是 8 字节，否则 ENABLE_DOUBLE_PRECISION 没生效，
     *    下游 fcl 会因类型不匹配而出问题。 */
    if (sizeof(ccd_real_t) != 8) {
        printf("FAIL ccd_real_t 为 %zu 字节，双精度未生效（fcl 需要双精度）\n",
               sizeof(ccd_real_t));
        return 1;
    }

    printf("libccd OK: 球体相交判定 3 例 + 长方体穿透深度 2 例精确吻合(<1e-9) + 双精度确认\n");
    return 0;
}
