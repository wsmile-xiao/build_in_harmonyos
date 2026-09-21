// Conan L1 test_package — consumer test for taocpp-sequences 3.0.1.
// Uses only the installed public headers via the exported CMake target
// taocpp::sequences; exercises real compile-time API calls.
#include <tao/seq/accumulate.hpp>
#include <tao/seq/functional.hpp>
#include <tao/seq/integer_sequence.hpp>
#include <tao/seq/make_integer_sequence.hpp>
#include <tao/seq/plus.hpp>
#include <tao/seq/multiplies.hpp>
#include <tao/seq/sum.hpp>
#include <tao/seq/prod.hpp>
#include <tao/seq/reverse.hpp>
#include <tao/seq/select.hpp>

#include <cassert>
#include <type_traits>

int main()
{
   using namespace tao::sequence;

   // Compile-time arithmetic over integer sequences.
   static_assert( sum< int, 1, 2, 3, 4 >::value == 10, "sum oops" );
   static_assert( prod< int, 2, 3, 4 >::value == 24, "prod oops" );
   static_assert( accumulate< op::plus, int, 1, 2, 3, 4, 5 >::value == 15, "accumulate plus oops" );
   static_assert( accumulate< op::multiplies, int, 1, 2, 3, 4 >::value == 24, "accumulate mult oops" );

   // make_integer_sequence + reverse produce a reversed sequence.
   using S = make_integer_sequence< int, 5 >;  // 0,1,2,3,4
   using R = reverse_t< S >;                   // 4,3,2,1,0
   static_assert( S::size() == 5, "size oops" );
   static_assert( R::size() == 5, "reverse size oops" );

   // Runtime observable result: expand the reversed sequence into an array.
   const int arr[ R::size() ] = { select< 0, R >::value, select< 1, R >::value,
                                  select< 2, R >::value, select< 3, R >::value,
                                  select< 4, R >::value };
   for( int i = 0; i < 5; ++i )
   {
      assert( arr[ i ] == 4 - i );
   }
   return 0;
}
