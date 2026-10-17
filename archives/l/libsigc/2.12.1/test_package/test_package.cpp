#include <sigc++/sigc++.h>

#include <cstdio>
#include <string>

namespace {

int free_calls = 0;

int add_ten(int value)
{
  ++free_calls;
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

bool check(bool condition, const char* message)
{
  if (!condition)
    std::fprintf(stderr, "FAIL: %s\n", message);
  return condition;
}

} // namespace

int main()
{
  bool ok = true;

  sigc::signal<int, int> signal;
  signal.connect(sigc::ptr_fun(&add_ten));
  ok &= check(signal.emit(5) == 15, "signal emits through ptr_fun");
  ok &= check(free_calls == 1, "free function called once");

  Receiver receiver;
  sigc::connection connection = signal.connect(
      sigc::mem_fun(receiver, &Receiver::doubled));
  ok &= check(signal.emit(7) == 14, "last slot result is returned");
  ok &= check(receiver.last == 14, "member slot updates receiver");
  ok &= check(signal.size() == 2, "signal contains two slots");

  connection.disconnect();
  ok &= check(!connection.connected(), "connection reports disconnected");
  ok &= check(signal.size() == 1, "disconnected slot is removed");
  ok &= check(signal.emit(1) == 11, "remaining slot still emits");

  {
    Receiver scoped;
    signal.connect(sigc::mem_fun(scoped, &Receiver::doubled));
    ok &= check(signal.size() == 2, "trackable slot is connected");
  }
  ok &= check(signal.size() == 1, "trackable slot disconnects on destruction");

  sigc::slot<int> bound = sigc::bind(sigc::ptr_fun(&add_ten), 32);
  ok &= check(bound() == 42, "bind fixes the function argument");

  std::string sink;
  sigc::signal<void, const std::string&> text_signal;
  text_signal.connect([&sink](const std::string& text) { sink = text; });
  text_signal.emit("harmonyos");
  ok &= check(sink == "harmonyos", "void signal delivers its payload");

  if (!ok)
    return 1;

  std::printf("libsigc++ 2.12.1 consumer checks passed\n");
  return 0;
}
