// test_flann.cpp — flann 1.9.2 consumer test (L1)
//
// 构造一个小型点集, 用 flann 的 C++ API 建一棵随机 kd-tree 索引并执行真实
// knn 搜索; 验证"数据集中某点的最近邻是其自身"(距离 0、索引命中)。
// 实质调用 flann::Matrix / Index<L2<>> / buildIndex / knnSearch, 非空壳。
#include <flann/flann.hpp>

#include <cstddef>
#include <cstdio>

int main() {
    using namespace flann;

    const std::size_t rows = 200;
    const std::size_t cols = 5;
    const std::size_t nn = 1;

    float* data = new float[rows * cols];
    for (std::size_t i = 0; i < rows * cols; ++i) {
        data[i] = static_cast<float>(i);  // 每个元素唯一, 每行唯一
    }
    Matrix<float> dataset(data, rows, cols);

    // 建 4 棵随机 kd-tree
    Index<L2<float> > index(dataset, KDTreeIndexParams(4));
    index.buildIndex();

    // 查询点 = 数据集第 7 行的精确副本, 其最近邻必然是自身
    const std::size_t probe = 7;
    float* q = new float[cols];
    for (std::size_t j = 0; j < cols; ++j) {
        q[j] = dataset[probe][j];
    }
    Matrix<float> query(q, 1, cols);

    Matrix<std::size_t> indices(new std::size_t[nn], 1, nn);
    Matrix<float> dists(new float[nn], 1, nn);

    index.knnSearch(query, indices, dists, nn, SearchParams(128));

    std::size_t* idx = indices.ptr();
    float* d = dists.ptr();
    std::printf("flann knnSearch: index=%zu dist=%f\n", idx[0], d[0]);

    int ok = (idx[0] == probe && d[0] == 0.0f);

    delete[] data;
    delete[] q;
    delete[] indices.ptr();
    delete[] dists.ptr();

    return ok ? 0 : 1;
}
