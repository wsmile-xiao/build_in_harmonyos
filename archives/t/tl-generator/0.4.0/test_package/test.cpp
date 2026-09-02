// test_package consumer test — tl-generator 0.4.0 on OHOS aarch64.
// Real usage of the packaged public API: tl::generator<T> coroutine generator.
#include <tl/generator.hpp>
#include <cstdio>
#include <string>
#include <vector>

// First N integers, symmetric to the upstream "firstn" sample.
tl::generator<int> firstn(int t) {
   int num = 0;
   while (num < t) {
      co_yield num;
      ++num;
   }
}

// Split a string_view by newlines, yielding vector<string> per line —
// exercises generator<std::vector<std::string>> like the upstream suite.
tl::generator<std::vector<std::string>> split_lines(std::string_view sv) {
   std::vector<std::string> line;
   std::string cur;
   for (char c : sv) {
      if (c == '\n') {
         line.push_back(cur);
         co_yield line;
         line.clear();
         cur.clear();
      } else {
         cur += c;
      }
   }
}

int main() {
   // 1) basic integer generator
   int i = 0;
   for (auto n : firstn(20)) {
      if (n != i) { std::printf("FAILED: firstn[%d]=%d\n", i, n); return 1; }
      ++i;
   }
   if (i != 20) { std::printf("FAILED: firstn produced %d values, want 20\n", i); return 2; }
   std::printf("ok: firstn produced 20 values in order\n");

   // 2) vector-of-strings generator (each line is one token string)
   auto gen = split_lines("alpha beta\ngamma delta\n");
   int lines = 0;
   for (auto&& line : gen) {
      if (line.size() != 1) { std::printf("FAILED: split line %d has %zu elems, want 1\n", lines, line.size()); return 3; }
      if (line[0].empty()) { std::printf("FAILED: split line %d empty\n", lines); return 4; }
      ++lines;
   }
   if (lines != 2) { std::printf("FAILED: split produced %d lines, want 2\n", lines); return 5; }
   std::printf("ok: split_lines produced 2 non-empty lines\n");

   std::printf("test_tl-generator: ALL PASSED\n");
   return 0;
}