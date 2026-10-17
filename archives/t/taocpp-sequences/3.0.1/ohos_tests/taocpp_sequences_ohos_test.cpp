/*
 * 鸿蒙专项测试：taocpp_sequences_ohos_test
 *
 * 目的：在 OHOS aarch64 工具链（clang 15 + libc++）构建并运行的 HarmonyOS
 * 专项用例，验证 taocpp-sequences 在 OHOS 平台编译期元编程能力真实可用：
 *   1. 仅通过公共头文件（tao/seq 下的 .hpp 头）与公开 API（make_index_sequence /
 *      map_t / sort_t / reverse_t / select / accumulate / op::plus）使用本库。
 *   2. 用编译期序列构建一张运行时查找表（LUT）：0..4 的平方经 sort 升序、
 *      reverse 反转后展开为 {16,9,4,1,0}，对确定性输入做反向查找，
 *      得到可观察的业务结果。
 *   3. 该用例与 test_package 消费者测试互补：本用例聚焦编译期算法在
 *      OHOS 工具链下的实际展开与运行形态验证。
 */
#include <tao/seq/functional.hpp>
#include <tao/seq/integer_sequence.hpp>
#include <tao/seq/make_integer_sequence.hpp>
#include <tao/seq/map.hpp>
#include <tao/seq/sort.hpp>
#include <tao/seq/reverse.hpp>
#include <tao/seq/select.hpp>
#include <tao/seq/accumulate.hpp>

#include <cstdio>
#include <type_traits>

namespace
{
   // 业务常量表：0..4 的平方 {0,1,4,9,16}（map 按索引挑选构造）
   using IDX = tao::sequence::make_index_sequence< 5 >;                 // std 0,1,2,3,4
   using SQR = tao::sequence::integer_sequence< int, 0, 1, 4, 9, 16 >;  // 平方表
   using SQ = tao::sequence::map_t< IDX, SQR >;                         // {0,1,4,9,16}
   using SRT = tao::sequence::sort_t< tao::sequence::op::less, SQ >;    // 升序 {0,1,4,9,16}
   using REV = tao::sequence::reverse_t< SRT >;                         // {16,9,4,1,0}

   // 将编译期序列展开为运行时常量数组（业务上层用法）
   template< typename >
   struct to_array
   {
   };

   template< typename T, T... Ns >
   struct to_array< tao::sequence::integer_sequence< T, Ns... > >
   {
      static constexpr T value[ sizeof...( Ns ) ] = { Ns... };
   };

   constexpr int lut_size = 5;
   const int( &lut )[ lut_size ] = to_array< REV >::value;
}  // namespace

int main()
{
   using namespace tao::sequence;

   static_assert( std::is_same< SQ, integer_sequence< int, 0, 1, 4, 9, 16 > >::value, "map result" );
   static_assert( std::is_same< SRT, integer_sequence< int, 0, 1, 4, 9, 16 > >::value, "sort result" );
   static_assert( std::is_same< REV, integer_sequence< int, 16, 9, 4, 1, 0 > >::value, "reverse result" );
   static_assert( accumulate< op::plus, int, 1, 2, 3, 4, 5 >::value == 15, "accumulate" );

   // 运行时查找表行为验证（可观察结果）
   int ok = 1;
   for( int i = 0; i < lut_size; ++i )
   {
      const int expected = ( lut_size - 1 - i ) * ( lut_size - 1 - i );
      if( lut[ i ] != expected )
      {
         std::printf( "OHOS test FAIL: lut[%d] = %d, expected %d\n", i, lut[ i ], expected );
         ok = 0;
      }
   }

   // select 按值取元素（公共 API 的运行时可用性）
   if( select< 0, REV >::value != 16 )
   {
      std::printf( "OHOS test FAIL: select<0,REV> = %d\n", select< 0, REV >::value );
      ok = 0;
   }

   std::printf( "OHOS test PASS: sorted/reversed square LUT = {16,9,4,1,0}, accumulate(1..5)=15\n" );
   return ok ? 0 : 1;
}
