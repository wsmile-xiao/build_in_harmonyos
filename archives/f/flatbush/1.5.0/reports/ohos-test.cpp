// HarmonyOS-specific test — flatbush 1.5.0
// 目的（非复述上游测试）：
//  1. 验证 OHOS 配方打包的头文件在 C++17（OHOS profile cppstd=17）下可直接使用，
//     且 FLATBUSH_SPAN 宏已由包传播（无宏时头文件要求 cxx_std_20 的 std::span）。
//  2. 验证 JS 兼容字节布局往返（from/data）：OHOS 上构建的索引可序列化为
//     与 JavaScript Flatbush 相同布局的 uint8 缓冲区并正确重建（跨语言互操作）。
#include <flatbush.h>

#include <cstdint>
#include <cstdio>
#include <vector>

#ifndef FLATBUSH_SPAN
#error "flatbush package must propagate FLATBUSH_SPAN for OHOS C++17 consumers"
#endif

int main() {
  using namespace flatbush;

  // C++17 + 自定义 span 路径（OHOS 配置）下构建 3 矩形 + 1 点
  FlatbushBuilder<double> builder;
  builder.add(Box<double>{0.0, 0.0, 1.0, 1.0});
  builder.add(Box<double>{2.0, 2.0, 3.0, 3.0});
  builder.add(Box<double>{10.0, 10.0, 20.0, 20.0});
  builder.add(Point<double>{100.0, 200.0});
  auto index = builder.finish();

  // bbox 搜索
  auto hits = index.search(Box<double>{0.0, 0.0, 1.5, 1.5});
  if (hits.size() != 1UL) {
    std::fprintf(stderr, "FAIL: search hits=%zu expected 1\n", hits.size());
    return 1;
  }

  // 最近邻（公开 API）
  auto neighbors = index.neighbors(Point<double>{0.5, 0.5}, 10);
  if (neighbors.empty() || neighbors[0] != 0) {
    std::fprintf(stderr, "FAIL: nearest neighbor expected id 0\n");
    return 1;
  }

  // JS 兼容字节布局：data() -> from() 往返，逐字节一致
  auto buffer = index.data();
  auto rebuilt = FlatbushBuilder<double>::from(buffer.data(), buffer.size());
  auto hits2 = rebuilt.search(Box<double>{2.0, 2.0, 3.0, 3.0});
  if (hits2.size() != 1UL || hits2[0] != 1) {
    std::fprintf(stderr, "FAIL: rebuilt search expected id 1\n");
    return 1;
  }

  // fromView（零拷贝视图，OHOS 大缓冲区场景；签名接受 span<const uint8_t>）
  std::vector<uint8_t> copy(buffer.begin(), buffer.end());
  auto viewed = FlatbushBuilder<double>::fromView(span<const uint8_t>{copy.data(), copy.size()});
  if (viewed.search(Box<double>{10.0, 10.0, 20.0, 20.0}).size() != 1UL) {
    std::fprintf(stderr, "FAIL: fromView search\n");
    return 1;
  }

  std::printf("PASS: OHOS C++17/FLATBUSH_SPAN + JS-compatible roundtrip ok\n");
  return 0;
}