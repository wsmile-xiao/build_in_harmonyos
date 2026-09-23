// test.cpp — gtkmm 4.0.0 消费者测试 (Conan L1, R34)
// 实质调用 gtkmm/gdkmm API 且不依赖显示服务器（OHOS Broadway 无窗口系统、
// gtk_init() 在 headless 下失败——见 0003 补丁对 3 个显示依赖测试的排除）。
// 本测试使用与上游 gdk_rgba_test 同款的无显示路径：Gdk::RGBA / Gdk::Rectangle
// 颜色与矩形运算 + sigc++-3.0 信号连接。任一声明失败返回非 0。
#include <gtkmm.h>
#include <gdkmm.h>
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

void on_clicked()
{
  // 信号回调：仅验证 sigc++ 连接可用，不触发 UI。
}

} // namespace

int main()
{
  bool ok = true;

  // 1. Gdk::RGBA —— 颜色构造 + 分量读取（gdkmm 公开 API，
  //    与上游 gdk_rgba_test 同路径：gtkmm 4.0.0 无 parse()，用
  //    set_rgba_u/get_red_u 等，不依赖显示）。
  Gdk::RGBA rgba;
  rgba.set_rgba_u(0xFFFF, 0x0000, 0x0000, 0xFFFF);
  ok &= check(rgba.get_red_u() == 0xFFFF, "Gdk::RGBA red_u");
  ok &= check(rgba.get_green_u() == 0x0000, "Gdk::RGBA green_u");
  ok &= check(rgba.get_blue_u() == 0x0000, "Gdk::RGBA blue_u");
  ok &= check(rgba.get_alpha_u() == 0xFFFF, "Gdk::RGBA alpha_u");

  // 2. Gdk::Rectangle —— 矩形构造 + 尺寸 + 求交（gdkmm 公开 API，无显示依赖）。
  Gdk::Rectangle r1(0, 0, 100, 50);
  Gdk::Rectangle r2(50, 25, 100, 100);
  ok &= check(r1.get_x() == 0 && r1.get_y() == 0 && r1.get_width() == 100 &&
              r1.get_height() == 50, "Gdk::Rectangle geometry");
  Gdk::Rectangle inter = r1.intersect(r2);
  ok &= check(inter.get_width() == 50 && inter.get_height() == 25,
              "Gdk::Rectangle intersect");

  // 3. sigc++-3.0 信号连接（libsigc-3.0 真实使用）。
  sigc::signal<void()> sig;
  sigc::connection conn = sig.connect(sigc::ptr_fun(&on_clicked));
  ok &= check(conn.connected(), "sigc++-3.0 signal connection");
  sig.emit();
  conn.disconnect();

  std::printf("gtkmm probe: checks=%d %s\n", g_checks, ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}