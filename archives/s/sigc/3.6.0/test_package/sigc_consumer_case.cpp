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

  // End-to-end consumer workflow: a typed signal, two receivers, mutation,
  // disconnect/RAII, bound invocation, and payload delivery.
  sigc::signal<int(int)> pipeline;
  pipeline.connect(sigc::ptr_fun(&add_ten));

  Receiver receiver;
  sigc::connection connection = pipeline.connect(
      sigc::mem_fun(receiver, &Receiver::doubled));

  ok &= check(pipeline.emit(5) == 10, "pipeline returns the final result");
  ok &= check(free_calls == 1 && receiver.last == 10, "all receivers process the event");
  ok &= check(pipeline.size() == 2, "pipeline contains both receivers");

  connection.disconnect();
  ok &= check(!connection.connected() && pipeline.size() == 1,
              "disconnect removes the member receiver");
  ok &= check(pipeline.emit(7) == 17, "remaining receiver still processes events");

  {
    Receiver scoped;
    pipeline.connect(sigc::mem_fun(scoped, &Receiver::doubled));
  }
  ok &= check(pipeline.size() == 1, "trackable receiver is removed at scope exit");

  sigc::slot<int()> bound = sigc::bind(sigc::ptr_fun(&add_ten), 32);
  ok &= check(bound() == 42, "bound invocation passes its argument");

  std::string sink;
  sigc::signal<void(const std::string&)> text_pipeline;
  text_pipeline.connect([&sink](const std::string& text) { sink = text; });
  text_pipeline.emit("harmonyos");
  ok &= check(sink == "harmonyos", "payload reaches the final consumer");

  if (!ok)
    return 1;

  std::printf("sigc consumer workflow passed\n");
  return 0;
}
