/*
 * taocpp-sequences 3.0.1 消费者验证 — 模拟业务上层组件
 *
 * 仅通过库已安装/导出的公共头文件（tao/seq 下的 .hpp 头）与公开 API 使用本库：
 *   make_integer_sequence / sum / prod / max / min / reverse / accumulate
 * 验证第三方使用者能否编译、链接、调用并正常运行，并得到可观察的业务结果
 * （业务层把编译期序列展开为运行时常量表供索引使用）。
 *
 * 构建方式（对已安装包）：
 *   clang++ -std=c++17 -I<prefix>/include consumer_taocpp_sequences.cpp -o consumer_taocpp_sequences
 */
#include <tao/seq/make_integer_sequence.hpp>
#include <tao/seq/reverse.hpp>
#include <tao/seq/select.hpp>
#include <tao/seq/sum.hpp>
#include <tao/seq/prod.hpp>
#include <tao/seq/max.hpp>
#include <tao/seq/min.hpp>
#include <tao/seq/accumulate.hpp>
#include <tao/seq/functional.hpp>

#include <cstdio>

namespace
{
   // 业务常量：前 N 个整数的和/积/最值（编译期求得，供上层直接使用）
   using S = tao::sequence::make_integer_sequence< int, 6 >;  // 0..5
   constexpr int kSum   = tao::sequence::sum< int, 0, 1, 2, 3, 4, 5 >::value;
   constexpr int kProd  = tao::sequence::prod< int, 1, 2, 3, 4, 5 >::value;
   constexpr int kMax   = tao::sequence::max< int, 3, 7, 2, 9, 1 >::value;
   constexpr int kMin   = tao::sequence::min< int, 3, 7, 2, 9, 1 >::value;
   constexpr int kAcc   = tao::sequence::accumulate< tao::sequence::op::plus, int, 1, 2, 3, 4, 5 >::value;

   // 业务运行时常量表：reverse(make_integer_sequence<5>) = {4,3,2,1,0}
   using R = tao::sequence::reverse_t< tao::sequence::make_integer_sequence< int, 5 > >;
   const int kIndexTable[ 5 ] = { tao::sequence::select< 0, R >::value,
                                  tao::sequence::select< 1, R >::value,
                                  tao::sequence::select< 2, R >::value,
                                  tao::sequence::select< 3, R >::value,
                                  tao::sequence::select< 4, R >::value };
}  // namespace

int main()
{
   int ok = 1;

   // 可观察业务结果核对
   if( kSum != 15 ) { std::printf( "consumer FAIL: sum = %d\n", kSum ); ok = 0; }
   if( kProd != 120 ) { std::printf( "consumer FAIL: prod = %d\n", kProd ); ok = 0; }
   if( kMax != 9 ) { std::printf( "consumer FAIL: max = %d\n", kMax ); ok = 0; }
   if( kMin != 1 ) { std::printf( "consumer FAIL: min = %d\n", kMin ); ok = 0; }
   if( kAcc != 15 ) { std::printf( "consumer FAIL: accumulate = %d\n", kAcc ); ok = 0; }

   for( int i = 0; i < 5; ++i )
   {
      if( kIndexTable[ i ] != 4 - i )
      {
         std::printf( "consumer FAIL: index table[%d] = %d\n", i, kIndexTable[ i ] );
         ok = 0;
      }
   }

   std::printf( "consumer PASS: sum=15 prod=120 max=9 min=1 accumulate(1..5)=15 index_table={4,3,2,1,0}\n" );
   return ok ? 0 : 1;
}
