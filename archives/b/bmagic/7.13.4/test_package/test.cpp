// test_package 消费者测试：真实调用 BitMagic 公开 API（R34 反空壳）
// 覆盖：bvector 位操作/集合代数/枚举器/范围计数、稀疏向量读写、
//       序列化往返、字符串稀疏向量读写。所有断言为真实语义校验。
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>

#include "bm.h"
#include "bmserial.h"
#include "bmsparsevec.h"
#include "bmstrsparsevec.h"
#include "bmalgo.h"

int main() {
    // 1. bvector 基本位操作（set/test/count/any）
    bm::bvector<> bv;
    bv.set(10);
    bv.set(100);
    bv.set(10000);
    assert(bv.count() == 3);
    assert(bv.test(10) && bv.test(100) && bv.test(10000));
    assert(!bv.test(11));
    assert(bv.any());

    // 2. 集合代数（AND/OR，结果语义）
    bm::bvector<> bv2;
    bv2.set(100);
    bv2.set(20000);
    bm::bvector<> ba(bv);
    ba.bit_and(bv2);
    assert(ba.count() == 1 && ba.test(100));
    bm::bvector<> bo(bv);
    bo.bit_or(bv2);
    assert(bo.count() == 4);

    // 3. 范围计数与枚举器遍历
    assert(bo.count_range(0, 1000) == 2);
    bm::bvector<>::enumerator en = bo.first();
    assert(*en == 10);
    ++en;
    assert(*en == 100);
    // get_first/get_next 全量遍历惯用法（上游文档口径）
    unsigned visited = 0;
    bm::bvector<>::size_type pos = bo.get_first();
    for (; pos != 0; pos = bo.get_next(pos)) {
        ++visited;
    }
    assert(visited == bo.count());

    // 4. 稀疏向量 sparse_vector<unsigned>：写读、默认零值语义
    bm::sparse_vector<unsigned, bm::bvector<> > sv;
    sv.set(0, 42);
    sv.set(1000000, 7);
    assert(sv[0] == 42);
    assert(sv[1000000] == 7);
    assert(sv[500000] == 0);
    assert(sv.size() == 1000001);

    // 5. 序列化往返（buffer 对象自动扩容 + bm::deserialize 消费字节数）
    bm::bvector<> bvs;
    for (unsigned i = 0; i < 100000; i += 7) {
        bvs.set(i);
    }
    bm::serializer<bm::bvector<> >::buffer sbuf;
    bm::serializer<bm::bvector<> > sz;
    sz.serialize(bvs, sbuf);
    bm::bvector<> bvd;
    size_t consumed = bm::deserialize(bvd, sbuf.buf());
    assert(consumed > 0);
    assert(bvd.equal(bvs));

    // 6. 字符串稀疏向量 str_sparse_vector：写入/读回一致
    bm::str_sparse_vector<char, bm::bvector<>, 32> ssv;
    ssv.set(0, "alpha");
    ssv.set(1, "beta");
    assert(ssv.size() == 2);
    std::string out;
    ssv.get(0, out);
    assert(out == "alpha");
    ssv.get(1, out);
    assert(out == "beta");

    std::printf("test_bmagic 7.13.4: ALL ASSERTIONS PASSED\n");
    return 0;
}
