#include <symengine/add.h>
#include <symengine/integer.h>
#include <symengine/symbol.h>

int main() {
    using SymEngine::add;
    using SymEngine::integer;
    using SymEngine::symbol;
    const auto expression = add(symbol("x"), integer(2));
    return expression->__str__().empty() ? 1 : 0;
}
