// test_csv2.cpp — 消费者 L1 测试: 实质调用 csv2 的 Reader 与 Writer API
// 验证安装后头文件可用、Reader 能正确解析带引号/trim 的 CSV、Writer 能输出 CSV。
#include <csv2/reader.hpp>
#include <csv2/writer.hpp>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

int main() {
  const char *path = "consumer_input.csv";
  {
    std::ofstream os(path, std::ios::trunc);
    os << "\"a\",\"b\",\"c\"\n"
       << "\"1\",\"2\",\"3\"\n"
       << "4, 5 , 6";
  }

  csv2::Reader<csv2::delimiter<','>, csv2::quote_character<'"'>,
               csv2::first_row_is_header<true>>
      reader;
  if (!reader.mmap(path)) {
    std::fprintf(stderr, "FAIL: mmap\n");
    return 1;
  }

  // header 行
  size_t h = 0;
  for (const auto cell : reader.header()) {
    std::string v;
    cell.read_value(v);
    if (v != "\"a\"" && v != "\"b\"" && v != "\"c\"") {
      std::fprintf(stderr, "FAIL: header cell [%s]\n", v.c_str());
      return 1;
    }
    ++h;
  }
  if (h != 3) {
    std::fprintf(stderr, "FAIL: header cols %zu\n", h);
    return 1;
  }

  // 数据行
  size_t rows = 0, cells = 0;
  for (const auto row : reader) {
    for (const auto cell : row) {
      std::string v;
      cell.read_value(v);
      ++cells;
    }
    ++rows;
  }
  if (rows != 2 || cells != 6) {
    std::fprintf(stderr, "FAIL: rows=%zu cells=%zu\n", rows, cells);
    return 1;
  }

  // Writer
  const char *out = "consumer_output.csv";
  {
    std::ofstream ofs(out, std::ios::trunc);
    csv2::Writer<csv2::delimiter<','>> writer(ofs);
    writer.write_row(std::vector<std::string>{"x", "y"});
  }
  std::ifstream ifs(out);
  std::string content((std::istreambuf_iterator<char>(ifs)),
                      std::istreambuf_iterator<char>());
  if (content != "x,y\n") {
    std::fprintf(stderr, "FAIL: writer output [%s]\n", content.c_str());
    return 1;
  }

  std::printf("csv2 consumer test: ALL PASSED\n");
  return 0;
}