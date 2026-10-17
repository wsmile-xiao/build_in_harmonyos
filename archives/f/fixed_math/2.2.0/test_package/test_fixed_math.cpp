// test_package 消费者探针 — fixed_math 2.2.0
// 通过已安装公开头文件 <fixedmath/fixed_math.hpp> 与 <fixedmath/iostream.h>
// 使用 fixed_t、公开数学 API 与字符串转换，验证第三方消费者可编译、链接、
// 调用并正常运行。
#include <fixedmath/fixed_math.hpp>
#include <fixedmath/iostream.h>
#include <iostream>
#include <string>

using fixedmath::fixed_t;
using fixedmath::operator""_fix;

int main()
  {
  using namespace fixedmath;

  // 1) 基础算术（constexpr 常量 + 公开运算符）
  constexpr fixed_t a{1.5_fix};
  constexpr fixed_t b{2.25_fix};
  constexpr fixed_t c = a + b;
  if(c != 3.75_fix)
    {
    std::cerr << "FAIL: 1.5+2.25 = " << c << " != 3.75" << std::endl;
    return 1;
    }

  // 2) 公开数学 API：sin(0)≈0、cos(0)≈1（fobj 函数对象，运行期调用；
  //    定点三角函数为查表近似，用误差带断言）
  fixed_t s0 = fobj::sin(0_fix);
  fixed_t c0 = fobj::cos(0_fix);
  fixed_t err = s0 * s0 + (c0 - 1_fix) * (c0 - 1_fix);
  if(err > fixed_t{0.001_fix})
    {
    std::cerr << "FAIL: sin(0)=" << s0 << " cos(0)=" << c0 << " err=" << err << std::endl;
    return 1;
    }

  // 3) func 命名空间函数形式：atan2(1,0)=π/2 > 0
  fixed_t pi_half = func::atan2(1_fix, 0_fix);
  if(pi_half <= 0_fix)
    {
    std::cerr << "FAIL: atan2(1,0)=" << pi_half << std::endl;
    return 1;
    }

  // 4) 字符串转换公开 API（iostream.h 暴露 from_string/to_string）
  auto parsed = from_string(std::string("3.99994"));
  if(!parsed || *parsed == 0_fix)
    {
    std::cerr << "FAIL: from_string(\"3.99994\")" << std::endl;
    return 1;
    }

  std::cout << "fixed_math consumer probe OK: c=" << c
            << " sin0=" << s0 << " cos0=" << c0
            << " atan2pi2=" << pi_half
            << " parsed=" << *parsed << std::endl;
  return 0;
  }
