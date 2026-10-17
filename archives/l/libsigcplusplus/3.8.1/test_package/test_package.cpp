/* Consumer test for libsigcplusplus 3.8.1 (libsigc++ 3.8.1, sigc++-3.0 ABI).
 * Exercises the real signals/slots API against the packaged libsigc-3.0
 * library: signal connect/emit, default last-value collector, connection
 * lifetime, scoped_connection, sigc::trackable auto-disconnect,
 * ptr_fun/mem_fun/bind slots and the exception_catch adaptor.
 */

#include <sigc++/sigc++.h>

#include <cstdio>
#include <memory>
#include <stdexcept>
#include <string>

namespace {

int free_calls = 0;
int caught_count = 0;

int add_ten(int value)
{
  ++free_calls;
  return value + 10;
}

struct throwing_functor
{
  int operator()(int)
  {
    throw std::runtime_error("slot failure");
  }
};

struct my_catcher
{
  int operator()()
  {
    try
    {
      throw;
    }
    catch (const std::exception&)
    {
      ++caught_count;
    }
    return -1;
  }
};

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
  bool all_ok = true;

  /* 1. lambda slot: emit doubles the argument */
  sigc::signal<int(int)> doubler;
  doubler.connect([](int x) { return x * 2; });
  all_ok &= check(doubler.emit(21) == 42, "lambda slot emit(21) == 42");

  /* 2. default collector returns the LAST slot's result */
  sigc::signal<int(int)> two_slots;
  two_slots.connect([](int x) { return x * 2; });
  two_slots.connect([](int x) { return x + 1; });
  all_ok &= check(two_slots.emit(21) == 22, "two-slot default collector returns last result");

  /* 3. connection::disconnect removes exactly one slot */
  sigc::signal<int(int)> connsig;
  sigc::connection first = connsig.connect([](int x) { return x * 2; });
  connsig.connect([](int x) { return x + 1; });
  all_ok &= check(first.connected(), "connection connected before disconnect");
  first.disconnect();
  all_ok &= check(!first.connected(), "connection disconnected");
  all_ok &= check(connsig.emit(21) == 22, "disconnected slot no longer runs");

  /* 4. ptr_fun free-function slot */
  sigc::signal<int(int)> freesig;
  freesig.connect(sigc::ptr_fun(&add_ten));
  all_ok &= check(freesig.emit(5) == 15, "ptr_fun slot add_ten(5) == 15");
  all_ok &= check(free_calls == 1, "ptr_fun slot invoked exactly once");

  /* 5. mem_fun slot on a trackable receiver */
  Receiver receiver;
  sigc::signal<int(int)> memsig;
  memsig.connect(sigc::mem_fun(receiver, &Receiver::doubled));
  all_ok &= check(memsig.emit(4) == 8, "mem_fun slot doubled(4) == 8");

  /* 6. destroying a trackable receiver auto-disconnects its slot */
  {
    Receiver temp;
    sigc::signal<int(int)> autosig;
    autosig.connect(sigc::mem_fun(temp, &Receiver::doubled));
    autosig.connect([](int x) { return x + 100; });
  } // temp destroyed -> its slot auto-disconnected
  all_ok &= check(memsig.emit(4) == 8, "surviving mem_fun slot still works");

  /* 7. bind fixes leading arguments */
  sigc::signal<int(int, int)> sumsig;
  sumsig.connect([](int a, int b) { return a + b; });
  auto bound = sigc::bind(sumsig, 40);
  all_ok &= check(bound(2) == 42, "bind(sumsig, 40)(2) == 42");

  /* 8. scoped_connection releases on scope exit */
  {
    sigc::signal<int(int)> scsig;
    scsig.connect([](int x) { return x * 2; });
    {
      sigc::scoped_connection guard = scsig.connect([](int x) { return x * 3; });
      all_ok &= check(scsig.emit(7) == 21, "scoped_connection active: last slot wins");
    }
    all_ok &= check(scsig.emit(7) == 14, "scoped_connection released on scope exit");
  }

  /* 9. exception_catch keeps a multi-listener emit alive when one throws */
  sigc::signal<int(int)> exsig;
  exsig.connect(sigc::exception_catch(throwing_functor(), my_catcher()));
  exsig.connect([](int x) { return x + 1; });
  all_ok &= check(exsig.emit(9) == 10, "exception_catch: emit survives a throwing slot");
  all_ok &= check(caught_count == 1, "exception_catch: catcher invoked exactly once");

  /* 10. empty signal returns a value-initialized result */
  sigc::signal<int(int)> empty;
  all_ok &= check(empty.emit(9) == 0, "empty signal emit returns value-initialized");

  if (!all_ok)
  {
    std::fprintf(stderr, "consumer test FAILED\n");
    return 1;
  }

  std::printf("libsigcplusplus 3.8.1 consumer test: all checks passed\n");
  return 0;
}
