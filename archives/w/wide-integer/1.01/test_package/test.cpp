#include <math/wide_integer/uintwide_t.h>

#include <iostream>
#include <string>

int main()
{
  // 消费者验证：仅通过公开头文件 <math/wide_integer/uintwide_t.h> 使用库 API。
  // 构造 512 位无符号大整数并执行乘法、除法、取模、字符串转换，
  // 验证第三方业务组件能够编译、链接并得到可观察的运算结果。
  using uint512_t = ::math::wide_integer::uintwide_t<512U, std::uint32_t>;

  const uint512_t a("123456789012345678901234567890123456789012345678901234567890");
  const uint512_t b("98765432109876543210987654321098765432109876543210987654321");

  const uint512_t mul = a * b;
  const std::string mul_str = ::math::wide_integer::to_string(mul);

  // python3 预算的精确结果（119 位，512 位类型可容纳）
  const std::string expected =
      "121932631137021795226185032733866788594511507391563633592367367779295611949397"
      "44871208653362292333223746380111126352690";

  const uint512_t div = a / b;
  const uint512_t rem = a % b;

  // 校验 (div * b + rem) == a
  const uint512_t rebuilt = (div * b) + rem;

  bool ok = true;
  if (mul_str != expected)
  {
    std::cerr << "FAIL: mul mismatch\n  got:      " << mul_str
              << "\n  expected: " << expected << "\n";
    ok = false;
  }
  if (rebuilt != a)
  {
    std::cerr << "FAIL: divmod round-trip mismatch\n";
    ok = false;
  }
  if (a % b != rem)
  {
    std::cerr << "FAIL: operator% mismatch\n";
    ok = false;
  }

  if (ok)
  {
    std::cout << "test_wide-integer OK: 512-bit mul/div/mod round-trip verified\n";
    return 0;
  }
  return 1;
}
