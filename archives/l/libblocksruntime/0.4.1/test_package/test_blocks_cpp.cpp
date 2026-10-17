// test_blocks_cpp.cpp — C++ consumer of the installed BlocksRuntime.
//
// Third consumer, different language front end: this target deliberately does
// NOT pass -fblocks itself, so it also proves that the packaged runtime
// propagates the language flag to consumers (cpp_info.cxxflags). It checks
// blocks capturing C++ objects (copy constructor on Block_copy), __block in
// C++, block arguments/returns and the retain/release lifecycle.
#include <cstdio>
#include <string>

#include <Block.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        checks++;                                                              \
        if (!(cond)) {                                                         \
            failures++;                                                        \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);        \
        }                                                                      \
    } while (0)

struct Tracker {
    int id;
    static int copies;
    explicit Tracker(int i) : id(i) {}
    Tracker(const Tracker &o) : id(o.id) { copies++; }
};

int Tracker::copies = 0;

static int apply_cpp(int (^f)(int), int v) { return f(v); }

int main()
{
    // 1. capture a std::string by value
    std::string s = "block";
    auto b1 = ^{ return s + "s"; };
    CHECK(b1() == "blocks");

    // 2. heap copy of a block capturing a C++ object outlives its scope
    std::string t = "heap";
    int (^b2)(void) = Block_copy(^{ return (int)t.size(); });
    CHECK(b2() == 4);
    Block_release(b2);

    // 3. parameters and return values
    int (^inc)(int) = ^(int x) { return x + 1; };
    CHECK(inc(41) == 42);

    // 4. __block in C++
    __block int total = 0;
    void (^acc)(int) = ^(int v) { total += v; };
    acc(40);
    acc(2);
    CHECK(total == 42);

    // 5. C++ copy constructor runs when the block is copied to the heap
    Tracker tr(7);
    Tracker::copies = 0;
    int (^getid)(void) = ^{ return tr.id; };
    CHECK(getid() == 7);
    int copies_stack = Tracker::copies;
    int (^heap_id)(void) = Block_copy(getid);
    CHECK(heap_id() == 7);
    CHECK(Tracker::copies > copies_stack);
    Block_release(heap_id);

    // 6. block as an argument
    CHECK(apply_cpp(^(int v) { return v * 3; }, 14) == 42);

    // 7. block returning a heap block
    typedef int (^IntBlock)(int);
    IntBlock (^maker)(int) = ^(int base) {
        return Block_copy(^(int x) { return x + base; });
    };
    IntBlock made = maker(40);
    CHECK(made(2) == 42);
    Block_release(made);

    // 8. nested block
    int (^outer)(int) = ^(int x) { return (^{ return x * 2; })(); };
    CHECK(outer(21) == 42);

    std::printf("test_blocks_cpp: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
