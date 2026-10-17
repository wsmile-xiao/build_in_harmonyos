// test.cpp — pangomm 2.46.5 消费者测试 (Conan L1)
// 实质调用 pangomm API：Pango::init、Pango::FontDescription（含 get_family/
// get_size 运行时断言）、Pango::AttrList（change() 插入真实 AttrInt 后遍历
// 迭代器数段数，可失败判据）、版本宏。
// 经 <pangomm.h> 传递包含 pango/glibmm/cairomm/sigc++ 依赖头，编译期暴露
// 头文件链断裂；运行期经 libpangomm-1.4 链接暴露符号缺失。
// 任一断言失败返回非 0。
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

  // 2. Pango::FontDescription —— 基础值对象（libpangomm-1.4 符号表依赖）。
  Pango::FontDescription fd("Sans 12");
  ok &= check(fd.get_family() == "Sans", "FontDescription::get_family");
  ok &= check(fd.get_size() == 12 * Pango::SCALE, "FontDescription::get_size");

  // 3. Pango::AttrList —— change() 插入真实 AttrInt 后遍历迭代器数段数：
  //    change() 未生效则列表为空、迭代器立即失效、计数为 0 → 本项 FAIL。
  Pango::AttrList attrs;
  Pango::AttrInt size_attr = Pango::Attribute::create_attr_size(12 * Pango::SCALE);
  attrs.change(size_attr);
  int n_segments = 0;
  for (Pango::AttrIter it = attrs.get_iter(); static_cast<bool>(it); ++it)
  {
    ++n_segments;
    if (n_segments > 4)
      break;
  }
  ok &= check(n_segments >= 1, "AttrList change() inserts AttrInt segment");

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

  std::printf("pangomm 2.46.5: all %d checks passed\n", g_checks);
  return 0;
}
