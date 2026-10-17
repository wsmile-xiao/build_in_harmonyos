#include <backward.hpp>
#include <cstdio>
#include <sstream>
#include <string>

// R34: substantive test — actually exercise the library API (stacktrace capture)
static int test_stacktrace() {
  backward::StackTrace st;
  st.load_here(32);
  if (st.size() == 0) {
    std::fprintf(stderr, "FAIL: empty stack trace\n");
    return 1;
  }
  // Resolve symbols (exercises dladdr path on OHOS)
  backward::TraceResolver tr;
  tr.load_stacktrace(st);
  std::ostringstream oss;
  backward::Printer printer;
  printer.object = true;
  printer.print(st, oss);
  std::string out = oss.str();
  if (out.empty()) {
    std::fprintf(stderr, "FAIL: no printed trace\n");
    return 1;
  }
  std::printf("%s", out.c_str());
  return 0;
}

int main() {
  if (test_stacktrace() != 0) {
    return 1;
  }
  std::printf("backward-cpp 1.6 test: OK\n");
  return 0;
}
