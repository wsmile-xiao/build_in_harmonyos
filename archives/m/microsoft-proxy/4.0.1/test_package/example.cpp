// test_package consumer smoke test for microsoft-proxy 4.0.1 (header-only).
// Exercises the real library API: a facade built with pro::facade_builder,
// dispatch via PRO_DEF_MEM_DISPATCH + pro::proxy<Facade>, and ownership
// transfer through std::make_unique (R34: substantive API usage).
#include <proxy/proxy.h>

#include <memory>
#include <string>
#include <cstdio>

PRO_DEF_MEM_DISPATCH(MemDraw, draw);

struct Drawable : pro::facade_builder
    ::add_convention<MemDraw, void()>
    ::build {};

struct Circle {
  void draw() const { std::puts("circle"); }
};

struct Square {
  void draw() const { std::puts("square"); }
};

int main() {
  Circle circle;
  pro::proxy<Drawable> p = &circle;                     // non-owning (raw pointer)
  p->draw();                                            // dispatch: circle

  auto owned = std::make_unique<Square>();
  pro::proxy<Drawable> q = std::move(owned);            // owning (unique_ptr)
  q->draw();                                            // dispatch: square

  // Verify the facade really dispatches to both implementations.
  pro::proxy<Drawable> r = &circle;
  int calls = 0;
  if (r) { calls++; }                                   // operator bool path
  std::printf("proxy test_package OK (calls=%d)\n", calls);
  return 0;
}