// test.cpp — pangomm 2.56.2 消费者测试 (Conan L1)
// 实质调用 pangomm API：Pango::init、Pango::FontDescription、Pango::AttrList
// （get_iter/AttrIter::next）、版本宏；经 <pangomm.h> 传递包含 pango/glibmm/
// cairomm/sigc++ 依赖头（含 pangomm/context.h 等），编译期暴露头文件链断裂，
// 运行期经 libpangomm-2.48 链接暴露符号缺失。
// 任一断言失败返回非 0（链接/头文件缺失也会在编译期暴露）。
// 注：本测试仅验证 pangomm 核心值对象路径，不实例化 Pango::Context 或
// Cairo::Context（后者需布局/字体映射环境，非本 L1 消费者测试范围）。
#include <pangomm.h>
#include <pangomm/init.h>
#include <pangommconfig.h>

#include <cstdio>
#include <string>

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

  // 1. Pango::init() —— 必须在使用 pango 对象前调用。
  Pango::init();

  // 2. Pango::FontDescription —— 基础值对象（libpangomm-2.48 符号表依赖）。
  Pango::FontDescription fd("Sans 12");
  ok &= check(fd.get_family() == "Sans", "FontDescription::get_family");
  ok &= check(fd.get_size() == 12 * Pango::SCALE, "FontDescription::get_size");

  // 3. Pango::AttrList —— 默认构造的列表必须为空：get_iter().next() 对空列表
  //    返回 false（pango_attr_iterator_next 语义）。若默认构造意外带属性即 FAIL。
  //    注：2.56.2 的 AttrList 无 C++ begin()/end()（仅 get_iter() 返回 AttrIter），
  //    故不用迭代器相等比较；此处 next() 是公开 API 中可直接断言"空"的方法。
  //    同时覆盖链接依赖（get_iter/AttrIter::next 在 libpangomm-2.48 符号表）。
  Pango::AttrList attrs;
  ok &= check(!attrs.get_iter().next(), "AttrList default ctor (empty: next() == false)");

  // 4. 版本宏：pangommconfig.h 由包提供。
#ifdef PANGOMM_MAJOR_VERSION
  ok &= check(PANGOMM_MAJOR_VERSION >= 2, "PANGOMM_MAJOR_VERSION defined");
#else
  ok = false;
  std::fprintf(stderr, "FAIL: PANGOMM_MAJOR_VERSION not defined (config header missing)\n");
#endif

  if (!ok)
  {
    std::fprintf(stderr, "pangomm test: %d checks, FAILURES present\n", g_checks);
    return 1;
  }

  std::printf("pangomm 2.56.2: all %d checks passed\n", g_checks);
  return 0;
}
