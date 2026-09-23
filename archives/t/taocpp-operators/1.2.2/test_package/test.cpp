#include <tao/operators.hpp>

#include <cassert>

class value : public tao::operators::addable<value>
{
public:
   explicit value( int v ) noexcept
      : value_( v )
   {
   }

   value& operator+=( const value& rhs ) noexcept
   {
      value_ += rhs.value_;
      return *this;
   }

   int get() const noexcept
   {
      return value_;
   }

private:
   int value_;
};

int main()
{
   const value lhs( 2 );
   const value rhs( 3 );
   assert( ( lhs + rhs ).get() == 5 );
   assert( ( value( 4 ) += value( 6 ) ).get() == 10 );
}
