// test.cpp — circularbuffer 1.4.0 消费者验证用例
// 仅通过已安装的公开头文件 <CircularBuffer.hpp> 使用公开 API：
// push / shift / pop / unshift / first / last / size / available /
// isEmpty / isFull / clear / copyToArray / operator[]
#include <CircularBuffer.hpp>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

static int failures = 0;

#define CHECK(cond, msg)                                    \
    do {                                                    \
        if (!(cond)) {                                      \
            std::fprintf(stderr, "FAIL: %s (%s:%d)\n",      \
                         msg, __FILE__, __LINE__);          \
            ++failures;                                     \
        }                                                   \
    } while (0)

int main() {
    // 容量 5 的 int32 环形缓冲
    CircularBuffer<int, 5> buf;

    CHECK(buf.isEmpty(), "new buffer should be empty");
    CHECK(!buf.isFull(), "new buffer should not be full");
    CHECK(buf.size() == 0, "new buffer size == 0");
    CHECK(buf.available() == 5, "new buffer available == 5");

    // FIFO push / shift
    CHECK(buf.push(10), "push 10 should succeed (no overwrite)");
    CHECK(buf.push(20), "push 20 should succeed");
    CHECK(buf.push(30), "push 30 should succeed");
    CHECK(buf.size() == 3, "size == 3 after three pushes");
    CHECK(buf.first() == 10, "first == 10 (FIFO order)");
    CHECK(buf.last() == 30, "last == 30 (FIFO order)");

    const int shifted = buf.shift();
    CHECK(shifted == 10, "shift returns 10");
    CHECK(buf.size() == 2, "size == 2 after shift");

    // LIFO push / pop
    CHECK(buf.push(40), "push 40 should succeed");
    const int popped = buf.pop();
    CHECK(popped == 40, "pop returns 40 (LIFO)");
    CHECK(buf.size() == 2, "size == 2 after pop");

    // unshift / first
    CHECK(buf.unshift(99), "unshift 99 should succeed");
    CHECK(buf.first() == 99, "first == 99 after unshift");

    // 填满到 overwrite 语义：push 返回 false 表示覆盖旧元素
    CHECK(buf.push(1), "push 1");
    CHECK(buf.push(2), "push 2");
    CHECK(buf.isFull(), "buffer should be full now");
    // 继续 push 会覆盖最早元素，返回 false
    const bool overwritten = buf.push(3);
    CHECK(!overwritten, "push on full buffer returns false (overwrite)");
    CHECK(buf.isFull(), "buffer remains full after overwrite");

    // copyToArray 顺序校验
    CircularBuffer<int, 8> buf2;
    for (int i = 1; i <= 4; ++i) {
        CHECK(buf2.push(i * 10), "fill buf2");
    }
    int out[8] = {0};
    buf2.copyToArray(out);
    CHECK(out[0] == 10 && out[1] == 20 && out[2] == 30 && out[3] == 40,
          "copyToArray preserves FIFO order");

    // operator[] 访问
    CHECK(buf2[0] == 10, "operator[] 0 == 10");
    CHECK(buf2[1] == 20, "operator[] 1 == 20");

    // clear
    buf2.clear();
    CHECK(buf2.isEmpty(), "clear empties the buffer");
    CHECK(buf2.available() == 8, "available == capacity after clear");

    // uint8_t 元素 + 小容量索引类型特化（IT=uint8_t 路径）
    CircularBuffer<uint8_t, 3> small;
    CHECK(small.push(200), "uint8 push 200");
    CHECK(small.push(201), "uint8 push 201");
    CHECK(small.first() == 200, "uint8 first == 200");
    CHECK(small.last() == 201, "uint8 last == 201");
    const uint8_t v = small.shift();
    CHECK(v == 200, "uint8 shift == 200");

    // capacity 编译期常量
    static_assert(CircularBuffer<int, 5>::capacity == 5,
                  "capacity must be 5");

    if (failures == 0) {
        std::printf("test_circularbuffer: ALL CHECKS PASSED\n");
        return 0;
    }
    std::printf("test_circularbuffer: %d CHECKS FAILED\n", failures);
    return 1;
}
