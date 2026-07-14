// test_package.cpp — libsigc++ 2.10.8 消费者测试
// 实际调用 libsigc++ API：signal 连接/发射、adaptor（bind/mem_fun/ptr_fun）、
// connection 断开、trackable 析构自动断开。任一断言失败返回非 0。
#include <sigc++/sigc++.h>

#include <cstdio>
#include <string>

namespace {

int g_free_calls = 0;

int add_ten(int value)
{
  ++g_free_calls;
  return value + 10;
}

class Receiver : public sigc::trackable
{
public:
  int doubled(int value)
  {
    last = value * 2;
    return last;
  }

  int last = 0;
};

bool check(bool condition, const char* what)
{
  if (!condition)
    std::fprintf(stderr, "FAIL: %s\n", what);
  return condition;
}

} // namespace

int main()
{
  bool ok = true;

  // 1. signal + ptr_fun 适配器：发射后返回最后一个 slot 的返回值。
  sigc::signal<int, int> sig;
  sig.connect(sigc::ptr_fun(&add_ten));
  ok &= check(sig.emit(5) == 15, "signal emit with ptr_fun slot");
  ok &= check(g_free_calls == 1, "free function called exactly once");

  // 2. mem_fun 适配器：成员函数作为 slot。
  Receiver receiver;
  sigc::connection conn = sig.connect(sigc::mem_fun(receiver, &Receiver::doubled));
  ok &= check(sig.emit(7) == 14, "signal emit returns last slot result");
  ok &= check(receiver.last == 14, "mem_fun slot updated receiver state");
  ok &= check(sig.size() == 2, "signal holds two slots");

  // 3. connection::disconnect() 之后该 slot 不再被调用。
  conn.disconnect();
  ok &= check(!conn.connected(), "connection reports disconnected");
  ok &= check(sig.size() == 1, "disconnect removed the slot");
  ok &= check(sig.emit(1) == 11, "remaining ptr_fun slot still emits");

  // 4. trackable：被跟踪对象析构时自动断开 slot（libsigc++ 的核心特性）。
  {
    Receiver scoped;
    sig.connect(sigc::mem_fun(scoped, &Receiver::doubled));
    ok &= check(sig.size() == 2, "scoped trackable slot connected");
  }
  ok &= check(sig.size() == 1, "trackable auto-disconnected on destruction");

  // 5. bind 适配器 + slot：绑定实参后调用。
  sigc::slot<int> bound = sigc::bind(sigc::ptr_fun(&add_ten), 32);
  ok &= check(bound() == 42, "sigc::bind fixes the argument");

  // 6. 无返回值 signal：验证 void 特化可用。
  std::string sink;
  sigc::signal<void, const std::string&> text_sig;
  text_sig.connect([&sink](const std::string& s) { sink = s; });
  text_sig.emit("harmonyos");
  ok &= check(sink == "harmonyos", "void signal delivered payload to lambda slot");

  if (!ok)
    return 1;

  std::printf("libsigc++ 2.10.8: all checks passed\n");
  return 0;
}
