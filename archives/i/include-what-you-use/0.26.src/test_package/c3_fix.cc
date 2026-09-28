// C3 用例：仅直接用到 Alpha，却包含了错误的间接头（文件可编译）。
// 期望 iwyu 报告添加直接头、移除间接头；
// 经 `iwyu 2>&1 | fix_includes.py` 管道改写后应含直接头、不含间接头、可编译。
// 注意：本注释不得出现头文件名（断言对 include 行做精确 grep，防自引用误匹配）。
#include "consumer_b.h"

int main() {
  Alpha a;
  (void)a.x;
  return 0;
}
