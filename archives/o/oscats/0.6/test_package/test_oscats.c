/* OSCATS 0.6 契约测试（鸿蒙 PC / OHOS aarch64 消费侧实跑）
 *
 * 上游无任何自动化测试（全仓 Makefile.am 无 TESTS/check_PROGRAMS，
 * examples/ 里的 ex0*.c 是需要 X/交互的演示程序），故由消费侧契约承担：
 * 用公开 API 跑一次真实的自适应测验（CAT）闭环，断言库产物可用。
 *
 * 流程（等价上游 examples/ex01.c 的最小化版本）：
 *   1D 连续潜变量空间 → 20 个 1PL 题项（b~N(0,1)）→ OscatsTest 注册
 *   SIMULATE/ESTIMATE/EXPOSURE_COUNTER/FIXED_LENGTH/CLOSEST_DIFF 算法
 *   → 3 个考生各作答 10 题 → 检查能力估计与题目曝光率。
 */
#include <stdio.h>
#include <math.h>
#include <glib.h>
#include <oscats.h>

#define N_ITEMS 20
#define LEN     10
#define N_EX    3

static int checks = 0;
static int fails = 0;

static void check(int ok, const char *msg)
{
  checks++;
  if (ok)
    printf("ok   - %s\n", msg);
  else
  {
    printf("FAIL - %s\n", msg);
    fails++;
  }
}

int main(void)
{
  OscatsSpace *space;
  OscatsItemBank *bank;
  OscatsTest *test;
  OscatsAlgExposureCounter *exposure;
  OscatsExaminee *examinees[N_EX];
  OscatsModel *model;
  OscatsItem *item;
  OscatsPoint *theta;
  OscatsDim dim = OSCATS_DIM_CONT + 0;   /* 第 0 个连续维度 */
  guint i;

  /* 1. 潜变量空间：一维连续 */
  space = g_object_new(OSCATS_TYPE_SPACE, "numCont", 1, NULL);
  check(OSCATS_IS_SPACE(space), "OscatsSpace constructed (OSCATS_IS_SPACE)");
  check(oscats_space_size(space) >= 1, "space size >= 1");
  /* 注意：oscats_space_dim_get_max() 只接受**自然**维度
   * （内部 g_return_val_if_fail((dim & OSCATS_DIM_TYPE_MASK) == OSCATS_DIM_NAT)），
   * 对连续维度调用会触发 GLib 断言。连续维度用 dim_get_name()/validate() 检查。 */
  check(g_strcmp0(oscats_space_dim_get_name(space, dim), "Cont.1") == 0,
        "continuous dim #0 registered with its default name (Cont.1)");
  check(oscats_space_validate(space, dim, 0) == TRUE,
        "continuous dim #0 is a valid dimension (oscats_space_validate)");

  /* 2. 题库：20 个 1PL 题项 */
  bank = g_object_new(OSCATS_TYPE_ITEM_BANK, "sizeHint", (guint) N_ITEMS, NULL);
  for (i = 0; i < N_ITEMS; i++)
  {
    model = g_object_new(OSCATS_TYPE_MODEL_L1P, "space", space, NULL);
    oscats_model_set_param_by_index(model, 0, oscats_rnd_normal(1));
    item = oscats_item_new(OSCATS_DEFAULT_KEY, model);
    oscats_item_bank_add_item(bank, OSCATS_ADMINISTRAND(item));
    g_object_unref(item);
  }
  check(OSCATS_IS_ITEM_BANK(bank), "OscatsItemBank constructed (OSCATS_IS_ITEM_BANK)");
  check(oscats_item_bank_num_items(bank) == (guint) N_ITEMS,
        "item bank holds exactly 20 items");

  /* 3. 测验 + CAT 算法 */
  test = g_object_new(OSCATS_TYPE_TEST, "id", "contract",
                      "itembank", bank, "length_hint", (guint) LEN, NULL);
  check(OSCATS_IS_TEST(test), "OscatsTest constructed (OSCATS_IS_TEST)");
  oscats_algorithm_register(g_object_new(OSCATS_TYPE_ALG_SIMULATE, NULL), test);
  oscats_algorithm_register(g_object_new(OSCATS_TYPE_ALG_ESTIMATE, NULL), test);
  exposure = (OscatsAlgExposureCounter *) oscats_algorithm_register(
      g_object_new(OSCATS_TYPE_ALG_EXPOSURE_COUNTER, NULL), test);
  g_object_ref(exposure);
  oscats_algorithm_register(
      g_object_new(OSCATS_TYPE_ALG_FIXED_LENGTH, "len", (guint) LEN, NULL),
      test);
  oscats_algorithm_register(
      g_object_new(OSCATS_TYPE_ALG_CLOSEST_DIFF, NULL), test);

  /* 4. 施测 */
  for (i = 0; i < N_EX; i++)
  {
    examinees[i] = g_object_new(OSCATS_TYPE_EXAMINEE, NULL);
    theta = oscats_point_new_from_space(space);
    oscats_point_set_cont(theta, dim, oscats_rnd_normal(1));
    oscats_examinee_set_sim_theta(examinees[i], theta);
    oscats_examinee_set_est_theta(examinees[i],
                                  oscats_point_new_from_space(space));
    oscats_point_set_cont(oscats_examinee_get_est_theta(examinees[i]), dim, 0);
    oscats_test_administer(test, examinees[i]);
    check(oscats_examinee_num_items(examinees[i]) == (guint) LEN,
          "examinee administered exactly 10 items");
    check(isfinite(oscats_point_get_cont(
              oscats_examinee_get_est_theta(examinees[i]), dim)),
          "estimated theta is finite after administration");
  }

  /* 5. 曝光率是概率 */
  {
    gdouble r = oscats_alg_exposure_counter_get_rate(
        exposure, OSCATS_ITEM(oscats_item_bank_get_item(bank, 0)));
    check(r >= 0.0 && r <= 1.0, "item exposure rate within [0,1]");
  }

  /* 清理 */
  for (i = 0; i < N_EX; i++)
    g_object_unref(examinees[i]);
  g_object_unref(exposure);
  g_object_unref(test);
  g_object_unref(bank);
  g_object_unref(space);

  printf("\n%d checks, %d failed\n", checks, fails);
  return fails == 0 ? 0 : 1;
}
