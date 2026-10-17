// test.cpp — glibmm 2.66.9 消费者测试 (Conan L1, R34)
// 实质调用 glibmm/giomm API：Glib::ustring、Glib::ustring::compose、
// Glib::convert、Glib::DateTime、Glib::RefPtr<Gio::File>、sigc 头文件集成。
// 任一声明失败返回非 0（链接/头文件缺失也会在编译期暴露）。
#include <glibmm.h>
#include <giomm.h>
#include <sigc++/sigc++.h>

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

  // 1. Glib::ustring —— UTF-8 字符串封装（libglibmm 内联/模板 + 符号表依赖）。
  Glib::ustring s = Glib::ustring("ohos") + "-glibmm";
  ok &= check(s == "ohos-glibmm", "Glib::ustring concat");
  ok &= check(s.size() == 11, "Glib::ustring::size");

  // 2. Glib::ustring::compose —— 非内联导出函数，强制真实链接 libglibmm-2.4。
  ok &= check(Glib::ustring::compose("%1 %2", "glibmm", "works") == "glibmm works",
              "Glib::ustring::compose");

  // 3. Glib::convert —— iconv 支撑的导出函数（libglibmm），往返转换。
  try
  {
    Glib::ustring conv = Glib::convert("abc", "UTF-8", "UTF-8");
    ok &= check(conv == "abc", "Glib::convert roundtrip");
  }
  catch (const Glib::ConvertError&)
  {
    ok = false;
    std::fprintf(stderr, "FAIL: Glib::convert threw\n");
  }

  // 4. Glib::DateTime —— glibmm 对 GDateTime 的绑定（经 glib 调用链）。
  // 2.66.x 的 Glib::DateTime 无 is_valid()/to_iso8601()（2.68 才有），
  // 验证构造成功 + get_year() 返回合理值即可。
  Glib::DateTime now = Glib::DateTime::create_now_local();
  ok &= check(now.get_year() >= 2020, "Glib::DateTime::create_now_local + get_year");

  // 5. giomm —— Gio::File（强制真实链接 libgiomm-2.4）。
  Glib::RefPtr<Gio::File> file = Gio::File::create_for_path("/tmp");
  ok &= check(bool(file), "Gio::File::create_for_path returns object");
  if (file)
    ok &= check(file->get_path() == "/tmp", "Gio::File::get_path");

  // 6. glibmm 头文件与 sigc++ 集成：Glib::SignalProxy 依赖 sigc::slot，
  // 直接验证 <sigc++/sigc++.h> 可用且与 glibmm 头文件共存。
  sigc::signal<void()> sig;
  bool fired = false;
  sig.connect([&fired]() { fired = true; });
  sig.emit();
  ok &= check(fired, "sigc::signal via glibmm header set");

  // 7. 版本宏：glibmmconfig.h 由 lib/glibmm-2.4/include 提供。
#ifdef GLIBMM_MAJOR_VERSION
  ok &= check(GLIBMM_MAJOR_VERSION >= 2, "GLIBMM_MAJOR_VERSION defined");
#else
  ok = false;
  std::fprintf(stderr, "FAIL: GLIBMM_MAJOR_VERSION not defined (config header missing)\n");
#endif

  if (!ok)
  {
    std::fprintf(stderr, "glibmm test: %d checks, FAILURES present\n", g_checks);
    return 1;
  }

  std::printf("glibmm 2.66.9: all %d checks passed\n", g_checks);
  return 0;
}
