#include "msd/channel.hpp"
#include "msd/static_channel.hpp"

#include <cassert>
#include <string>

// Consumer-side verification (R34): actually exercise the msd::channel API
// instead of printing a dummy string.
int main()
{
    // Unbuffered channel with default storage (queue).
    msd::channel<int> ch;
    assert(ch.empty());

    ch << 1 << 2 << 3;
    assert(ch.size() == 3u);
    assert(!ch.empty());

    int out = 0;
    ch >> out;
    assert(out == 1);
    ch >> out;
    assert(out == 2);
    ch >> out;
    assert(out == 3);
    assert(ch.empty());

    // write()/read() API and close()/drained() semantics.
    assert(ch.write(42));
    assert(ch.read(out));
    assert(out == 42);
    ch.close();
    assert(ch.closed());
    assert(ch.drained());
    assert(!ch.write(99));  // write on closed channel returns false

    // Static (bounded) channel with array storage.
    msd::static_channel<std::string, 2> sch;
    assert(sch.write("hello"));
    assert(sch.write("world"));
    assert(sch.size() == 2u);

    std::string s;
    assert(sch.read(s));
    assert(s == "hello");
    assert(sch.read(s));
    assert(s == "world");
    assert(sch.empty());
    sch.close();
    assert(sch.drained());

    return 0;
}