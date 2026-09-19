#include <igloo/igloo_alt.h>

using namespace igloo;

Describe(consumer_guitar_test)
{
  It(asserts_integer_equality)
  {
    Assert::That(2 + 2, Is().EqualTo(4));
  }

  It(asserts_string_content)
  {
    Assert::That(std::string("igloo works"), Is().Containing("works"));
  }
};

int main(int argc, const char *argv[])
{
  return TestRunner::RunAllTests(argc, argv);
}