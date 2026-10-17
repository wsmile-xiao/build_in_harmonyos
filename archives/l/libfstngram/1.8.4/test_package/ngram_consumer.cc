// libfstngram 1.8.4 consumer smoke test.
//
// 真跑消费者：链接**已安装**的 libfstngram 静态/动态产物，调用其 out-of-line 实现
// （BitmapIndex::Rank1/Select 在 bitmap-index.o，nth_bit 在 nthbit.o），断言结果。
// 头文件是 inline 模板，仅凭头文件无法证明产物本身可用；本程序把链接期与运行期
// 都覆盖到交付的库文件上。
#include <cstdint>
#include <cstdio>
#include <cstdlib>

#include <fst/extensions/ngram/bitmap-index.h>
#include <fst/extensions/ngram/nthbit.h>

int main() {
  static uint64_t bits[2] = {0, 0};  // 128-bit bitmap
  fst::BitmapIndex::Set(bits, 0);
  fst::BitmapIndex::Set(bits, 3);
  fst::BitmapIndex::Set(bits, 64);
  fst::BitmapIndex::Set(bits, 70);

  fst::BitmapIndex index(bits, 128, /*enable_select_0_index=*/true,
                         /*enable_select_1_index=*/true);

  if (index.Bits() != 128) {
    std::fprintf(stderr, "FAIL Bits()=%zu\n", index.Bits());
    return 1;
  }
  if (index.GetOnesCount() != 4) {
    std::fprintf(stderr, "FAIL GetOnesCount()=%zu\n", index.GetOnesCount());
    return 2;
  }
  if (index.Rank1(4) != 2) {  // positions 0..3 -> {0, 3}
    std::fprintf(stderr, "FAIL Rank1(4)=%zu\n", index.Rank1(4));
    return 3;
  }
  if (index.Rank1(65) != 3) {  // positions 0..64 -> {0, 3, 64}
    std::fprintf(stderr, "FAIL Rank1(65)=%zu\n", index.Rank1(65));
    return 4;
  }
  if (index.Rank1(128) != 4) {
    std::fprintf(stderr, "FAIL Rank1(128)=%zu\n", index.Rank1(128));
    return 5;
  }
  if (index.Select1(3) != 70) {
    std::fprintf(stderr, "FAIL Select1(3)=%zu\n", index.Select1(3));
    return 6;
  }
  // bits[1] = bit0 (global 64) | bit6 (global 70) -> the 0th one-bit is 0,
  // the 1st one-bit is 6.
  if (fst::nth_bit(bits[1], 0) != 0 || fst::nth_bit(bits[1], 1) != 6) {
    std::fprintf(stderr, "FAIL nth_bit(bits[1],0)=%d nth_bit(bits[1],1)=%d\n",
                 fst::nth_bit(bits[1], 0), fst::nth_bit(bits[1], 1));
    return 7;
  }

  std::printf(
      "libfstngram consumer OK: ones=%zu Rank1(65)=%zu Select1(3)=%zu "
      "nth_bit0=%d nth_bit1=%d\n",
      index.GetOnesCount(), index.Rank1(65), index.Select1(3),
      fst::nth_bit(bits[1], 0), fst::nth_bit(bits[1], 1));
  return 0;
}
