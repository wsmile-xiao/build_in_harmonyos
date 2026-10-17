// test.cpp — atkmm 2.36.4 消费者测试 (Conan L1)
// 实质调用 atkmm API：Atk::init()、Glib::wrap(AtkObject*) 绑定包装、
// StateSet 工厂+状态增删查、Relation 工厂+类型往返、Object 名称访问器、
// 版本宏——覆盖绑定核心面。
// 任一声明失败返回非 0（链接/头文件缺失也会在编译期暴露）。
#include <atkmm.h>
#include <atkmm/init.h>
#include <atkmmconfig.h>

#include <atk/atk.h> // atk_no_op_object_new（C 侧工厂，经绑定包装后驱动 C++ 面）

#include <cstdio>
#include <string>
#include <vector>

namespace {

int g_checks = 0;

bool check(bool condition, const char* what)
{
  ++g_checks;
  if (!condition)
    std::fprintf(stderr, "FAIL: %s\n", what);
  return condition;
}

} // namespace

int main()
{
  bool ok = true;

  // 1. Atk::init() —— 绑定初始化。
  Atk::init();

  // 2. 版本宏与 pkg-config 一致性（atkmm-2.36 ABI）。
  ok &= check(ATKMM_MAJOR_VERSION == 2, "ATKMM_MAJOR_VERSION == 2");
  ok &= check(ATKMM_MINOR_VERSION == 36, "ATKMM_MINOR_VERSION == 36");
  ok &= check(ATKMM_MICRO_VERSION == 4, "ATKMM_MICRO_VERSION == 4");

  // 3. C 对象 + Glib::wrap() 绑定包装 → C++ 访问器（核心绑定路径）。
  // atk_no_op_object_new(GObject*) 接收被代理的 GObject（此处用裸 GObject 演示）。
  GObject* gobj_c = static_cast<GObject*>(g_object_new(G_TYPE_OBJECT, nullptr));
  AtkObject* cobj = ATK_OBJECT(atk_no_op_object_new(gobj_c));
  Glib::RefPtr<Atk::Object> obj = Glib::wrap(cobj); // atkmm 绑定 wrap（引用移交）
  ok &= check(static_cast<bool>(obj), "Glib::wrap(AtkObject*) non-null");
  obj->set_name("atkmm-harmonyos");
  ok &= check(obj->get_name() == "atkmm-harmonyos", "set_name/get_name round-trip");
  ok &= check(obj->get_role() == Atk::Role::INVALID, "NoOpObject default role INVALID");

  // 4. Atk::StateSet 工厂构造 + 状态增删查（enum class StateType）。
  auto stateset = Atk::StateSet::create();
  ok &= check(static_cast<bool>(stateset), "StateSet::create() non-null");
  ok &= check(stateset->is_empty(), "fresh StateSet is_empty");
  stateset->add_state(Atk::StateType::ACTIVE);
  ok &= check(stateset->contains_state(Atk::StateType::ACTIVE), "contains ACTIVE after add");
  ok &= check(!stateset->is_empty(), "StateSet not empty after add");
  stateset->remove_state(Atk::StateType::ACTIVE);
  ok &= check(stateset->is_empty(), "StateSet empty after remove");

  // 5. Atk::Relation 工厂构造（enum class Relation::Type）。
  std::vector<Glib::RefPtr<Atk::Object>> targets;
  targets.push_back(obj);
  auto relation = Atk::Relation::create(targets, Atk::Relation::Type::LABELLED_BY);
  ok &= check(static_cast<bool>(relation), "Relation::create() non-null");
  ok &= check(relation->get_relation_type() == Atk::Relation::Type::LABELLED_BY,
              "Relation type round-trip");

  if (!ok)
  {
    std::fprintf(stderr, "atkmm consumer test: FAILED\n");
    return 1;
  }
  std::printf("atkmm consumer test: PASS (%d checks)\n", g_checks);
  return 0;
}
