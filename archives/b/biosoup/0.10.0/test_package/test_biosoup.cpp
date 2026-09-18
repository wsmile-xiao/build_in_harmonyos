// Consumer test for biosoup: exercise the Sequence data structure
// (construction, unique ids, reverse-and-complement transformation).
// 上游 header-only 惯例：静态计数器由使用者 TU 提供类外定义
// （与上游 test/sequence_test.cpp:7 一致）。
#include <atomic>
#include <cstdint>
#include <iostream>

#include "biosoup/sequence.hpp"

std::atomic<std::uint32_t> biosoup::Sequence::num_objects{0};

namespace {

int fail(const char* what) {
    std::cerr << "FAIL: " << what << std::endl;
    return 1;
}

}  // namespace

int main() {
    // 构造：name/data/quality 字段真实落位
    biosoup::Sequence s{"seq1", "ACGTT"};
    if (s.name != "seq1") return fail("name mismatch");
    if (s.data != "ACGTT") return fail("data mismatch");

    // num_objects 原子计数：不同对象 id 必须不同
    biosoup::Sequence t{"seq2", "TTTT"};
    if (s.id == t.id) return fail("ids not unique");

    // 带质量值构造
    biosoup::Sequence q{"sq", "AC", "II"};
    if (q.quality != "II") return fail("quality mismatch");

    // ReverseAndComplement：ACGTT -> 互补 TGCAA -> 反转 AACGT
    s.ReverseAndComplement();
    if (s.data != "AACGT") return fail("reverse-and-complement mismatch");

    std::cout << "biosoup consumer test PASS" << std::endl;
    return 0;
}
