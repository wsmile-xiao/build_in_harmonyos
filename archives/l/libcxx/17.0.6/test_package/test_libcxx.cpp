// libcxx 17.0.6 smoke test for HarmonyOS PC.
// Verifies the three adaptations actually unlock modern C++20 usage with
// clang 15: std::format, std::views, and construct_at for aggregates.
#include <format>
#include <ranges>
#include <vector>
#include <string>
#include <cstdio>

// Aggregate used to exercise construct_at (the is_aggregate dispatch).
struct Point {
  int x;
  int y;
};

int main() {
  std::string s = std::format("{} {:.2f}", 42, 3.14159);
  if (s != "42 3.14") {
    std::fprintf(stderr, "FAIL: std::format mismatch: %s\n", s.c_str());
    return 1;
  }
  std::vector<int> v{1, 2, 3};
  auto t = std::views::transform(v, [](int i) { return i * 2; });
  int sum = 0;
  for (int x : t) sum += x;
  if (sum != 12) {
    std::fprintf(stderr, "FAIL: std::views::transform sum=%d\n", sum);
    return 2;
  }
  // Aggregate construction through the standard allocator (construct_at).
  std::vector<Point> pts;
  pts.emplace_back(3, 4);
  pts.emplace_back(5, 6);
  if (pts.size() != 2 || pts[1].x != 5 || pts[1].y != 6) {
    std::fprintf(stderr, "FAIL: aggregate construct_at\n");
    return 3;
  }
  std::printf("OK: format=%s sum=%d points=%zu\n", s.c_str(), sum, pts.size());
  return 0;
}
