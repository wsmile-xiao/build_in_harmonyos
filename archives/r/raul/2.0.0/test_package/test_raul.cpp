// raul 2.0.0 消费者测试（R34：真实调用已安装的公共 API，非空壳）。
// 覆盖 Symbol / Path / Array / RingBuffer / Semaphore / DoubleBuffer / Maid，
// 共 40 项断言（与 test_package/MANIFEST.yml 的 assertion_count 对应）。
#undef NDEBUG

#include "raul/Array.hpp"
#include "raul/DoubleBuffer.hpp"
#include "raul/Maid.hpp"
#include "raul/Path.hpp"
#include "raul/RingBuffer.hpp"
#include "raul/Semaphore.hpp"
#include "raul/Symbol.hpp"

#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <string>

int
main()
{
  // ── Symbol：合法性、symbolify、非法构造抛异常 ──
  assert(raul::Symbol::is_valid("foo_bar42"));                        // 1
  assert(!raul::Symbol::is_valid("42foo"));                           // 2
  assert(!raul::Symbol::is_valid(""));                                // 3
  assert(raul::Symbol::symbolify("hello world!") == "hello_world_");  // 4
  assert(raul::Symbol::symbolify("123") == "_123");                   // 5

  bool threw = false;
  try {
    const raul::Symbol bad("not a symbol!");
    (void)bad;
  } catch (const raul::Symbol::BadSymbol&) {
    threw = true;
  }
  assert(threw);                                                      // 6

  // ── Path：根/父/子/符号/LCA ──
  const raul::Path root;
  assert(root.is_root());                                             // 7
  const raul::Path path("/foo/bar");
  assert(!path.is_root());                                            // 8
  assert(std::string(path.symbol()) == "bar");                        // 9
  assert(path.parent() == raul::Path("/foo"));                        // 10
  assert(path.parent().is_parent_of(path));                           // 11
  assert(root.child(path) == path);                                   // 12
  assert(raul::Path::lca(raul::Path("/a/b/c"), raul::Path("/a/b/d")) ==
         raul::Path("/a/b"));                                         // 13

  // ── Array：构造/填充/扩容/拷贝 ──
  raul::Array<int> array(8, 3);
  assert(array.size() == 8);                                          // 14
  assert(array[0] == 3 && array[7] == 3);                             // 15
  array.alloc(4, 7);
  assert(array.size() == 4);                                          // 16
  assert(array.at(3) == 7);                                           // 17
  raul::Array<int> copy(array);
  assert(copy.size() == 4 && copy[0] == 7);                           // 18

  // ── RingBuffer：写入/peek/读取/空间核算 ──
  raul::RingBuffer ring(64);
  assert(ring.capacity() == 63);                                      // 19
  const char* const message = "hello raul";
  assert(ring.write(10, message) == 10);                              // 20
  assert(ring.read_space() == 10);                                    // 21
  char buffer[16] = {0};
  assert(ring.peek(10, buffer) == 10);                                // 22
  assert(std::strncmp(buffer, message, 10) == 0);                     // 23
  assert(ring.read(10, buffer) == 10);                                // 24
  assert(ring.read_space() == 0);                                     // 25
  assert(ring.write_space() == ring.capacity());                      // 26

  // ── Semaphore：try_wait/timed_wait/post ──
  raul::Semaphore semaphore(0);
  assert(!semaphore.try_wait());                                      // 27
  assert(!semaphore.timed_wait(std::chrono::milliseconds(1)));        // 28
  semaphore.post();
  assert(semaphore.try_wait());                                       // 29
  assert(!semaphore.try_wait());                                      // 30

  // ── DoubleBuffer：原子设置与读取 ──
  raul::DoubleBuffer<int> double_buffer(1);
  assert(double_buffer.get() == 1);                                   // 31
  assert(double_buffer.set(2));                                       // 32
  assert(double_buffer.get() == 2);                                   // 33
  assert(double_buffer.set(3));                                       // 34
  assert(double_buffer.get() == 3);                                   // 35

  // ── Maid：managed_ptr 延迟回收 ──
  raul::Maid maid;
  assert(maid.empty());                                               // 36
  {
    raul::managed_ptr<raul::Array<int>> managed =
      maid.make_managed<raul::Array<int>>(4, 9);
    assert(managed->size() == 4 && (*managed)[0] == 9);               // 37
    assert(maid.empty());                                             // 38
  }
  assert(!maid.empty());                                              // 39
  maid.cleanup();
  assert(maid.empty());                                               // 40

  std::printf("raul consumer test PASSED: 40 assertions\n");
  return 0;
}
