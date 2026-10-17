// Boost::serialization consumer — 1.90.0.4.3 新增。
// 验证：
//   1. CMakeDeps 真的生成了 Boost::serialization 目标（否则 configure 即失败）；
//   2. 链接到 libboost_serialization.so（否则 link 即失败）；
//   3. 运行期做一次 vector<int> 的 binary archive 往返，断言数据一致。
// 这正是 sfcgal 16 个头文件 #include <boost/archive/...> 所需的最小能力。
#include <boost/archive/binary_iarchive.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/serialization/vector.hpp>

#include <cassert>
#include <sstream>
#include <vector>

int main() {
    std::vector<int> original{1, 1, 2, 3, 5, 8, 13, 21};

    std::stringstream ss(std::ios::in | std::ios::out | std::ios::binary);
    {
        boost::archive::binary_oarchive oa(ss);
        oa & original;
    }

    std::vector<int> restored;
    {
        boost::archive::binary_iarchive ia(ss);
        ia & restored;
    }

    assert(restored.size() == original.size());
    for (std::size_t i = 0; i < original.size(); ++i) {
        assert(restored[i] == original[i]);
    }
    return 0;
}
