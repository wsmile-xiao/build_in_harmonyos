// Conan L1 test — flatbush 1.5.0
// 真实调用 flatbush 公开 API（R34）：构建索引、bbox 搜索、最近邻查询
#include <flatbush.h>
#include <cstddef>
#include <cstdlib>
#include <iostream>

int main() {
  using namespace flatbush;

  // 构建索引（与上游 tests/package/main.cpp 同型消费者用例）
  FlatbushBuilder<double> builder;
  builder.add(Box<double>{0.0, 0.0, 1.0, 1.0});
  builder.add(Box<double>{4.0, 4.0, 5.0, 5.0});
  builder.add(Point<double>{10.0, 20.0});
  auto index = builder.finish();

  // bbox 搜索
  auto hits = index.search(Box<double>{0.0, 0.0, 1.0, 1.0});
  if (hits.size() != 1UL) {
    std::cerr << "FAIL: search hits=" << hits.size() << " expected 1\n";
    return 1;
  }

  // 最近邻查询（公开 API）
  auto neighbors = index.neighbors(Point<double>{0.5, 0.5}, /*maxResults=*/5);
  if (neighbors.empty()) {
    std::cerr << "FAIL: neighbors empty\n";
    return 1;
  }

  // 跨类型重建（公开 API，验证字节布局可移植性）
  auto buffer = index.data();
  auto rebuilt = FlatbushBuilder<double>::from(buffer.data(), buffer.size());
  auto hits2 = rebuilt.search(Box<double>{0.0, 0.0, 1.0, 1.0});
  if (hits2.size() != 1UL) {
    std::cerr << "FAIL: rebuilt search hits=" << hits2.size() << " expected 1\n";
    return 1;
  }

  std::cout << "PASS: flatbush L1 consumer test ok ("
            << hits.size() << " bbox hit, " << neighbors.size()
            << " neighbor(s), rebuilt ok)\n";
  return 0;
}