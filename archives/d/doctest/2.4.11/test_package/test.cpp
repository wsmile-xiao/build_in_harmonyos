#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>
#include <string>
TEST_CASE("consumer arithmetic"){ CHECK(2+3==5); }
TEST_CASE("consumer string API"){
 const std::string value="HarmonyOS";
 CHECK(value.size()==9);
 CHECK(value.substr(0,7)=="Harmony");
}
