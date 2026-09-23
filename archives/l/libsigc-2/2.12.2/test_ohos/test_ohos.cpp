// OHOS delivery test — real signal/slot execution on OpenHarmony PC.
//
// This is the binary executed by test_ohos.sh (H7). It re-exercises the
// core consumer API paths — signal/slot, return values, connection
// disconnect, trackable lifetime, member-function binding, bound and
// lambda slots, and the exception path — against the FINAL Conan package
// installed in the Conan cache, linked exactly like a downstream project.
#include <sigc++/sigc++.h>

#include <cstdio>
#include <stdexcept>
#include <string>

namespace {

int add_ten(int value)
{
  return value + 10;
}

int throwing_slot(int)
{
  throw std::runtime_error("slot failure");
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

  Receiver receiver;
  sigc::connection connection = signal.connect(
      sigc::mem_fun(receiver, &Receiver::doubled));
  ok &= check(signal.emit(7) == 14, "last slot result is returned");
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
  text_signal.emit("openharmony");
  ok &= check(sink == "openharmony", "void signal delivers its payload");

  sigc::signal<int, int> failing;
  failing.connect(sigc::ptr_fun(&throwing_slot));
  bool caught = false;
  try
  {
    failing.emit(3);
  }
  catch (const std::runtime_error& error)
  {
    caught = std::string(error.what()) == "slot failure";
  }
  ok &= check(caught, "slot exception propagates through emit");

  if (!ok)
    return 1;

  std::printf("libsigc++ 2.12.2 OHOS delivery checks passed\n");
  return 0;
}
