// Consumer test 1/2: exercise the installed library's version API.
//
// Covers e57::Version::astm/astmMajor/astmMinor/library/get using only the
// installed headers + libE57Format (7 checks; any failure exits non-zero).
#include <iostream>
#include <string>

#include <E57Format/E57Version.h>

namespace
{
int g_checks = 0;
int g_failed = 0;

void check( bool cond, const char *name )
{
   ++g_checks;
   if ( cond )
   {
      std::cout << "ok " << g_checks << ": " << name << "\n";
   }
   else
   {
      ++g_failed;
      std::cout << "FAIL " << g_checks << ": " << name << "\n";
   }
}
} // namespace

int main()
{
   check( e57::Version::astm() == "1.0", "ASTM version string is 1.0" );
   check( e57::Version::astmMajor() == 1, "ASTM major is 1" );
   check( e57::Version::astmMinor() == 0, "ASTM minor is 0" );

   const std::string library = e57::Version::library();
   std::cout << "info: library id: " << library << "\n";
   check( library.compare( 0, 15, "E57Format-3.3.0" ) == 0,
          "library id starts with E57Format-3.3.0" );

   uint32_t major = 0;
   uint32_t minor = 0;
   std::string id;
   e57::Version::get( major, minor, id );
   check( major == e57::Version::astmMajor(), "get() major matches astmMajor()" );
   check( minor == e57::Version::astmMinor(), "get() minor matches astmMinor()" );
   check( id == library, "get() id matches library()" );

   std::cout << "RESULT: " << ( g_checks - g_failed ) << "/" << g_checks
             << " checks passed\n";
   return g_failed == 0 ? 0 : 1;
}
