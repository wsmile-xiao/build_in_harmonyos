/// Consumer test for lutok: exercises the packaged RAII wrapper over the Lua
/// C API through the installed public headers only.
#include <cstdlib>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

#include <lutok/c_gate.hpp>
#include <lutok/exceptions.hpp>
#include <lutok/operations.hpp>
#include <lutok/stack_cleaner.hpp>
#include <lutok/state.ipp>


static int
native_multiply(lutok::state& state)
{
    if (!state.is_number(-2) || !state.is_number(-1))
        throw std::runtime_error("arguments must be numbers");
    state.push_integer(state.to_integer(-2) * state.to_integer(-1));
    return 1;
}


int
main(void)
{
    int checks = 0;

    lutok::state state;
    state.open_all();

    const unsigned int results = lutok::do_string(state, "return 1 + 1", 0, 1, 0);
    if (results != 1 || !state.is_number(-1) || state.to_integer(-1) != 2) {
        std::cerr << "unexpected result from Lua\n";
        return EXIT_FAILURE;
    }
    ++checks;
    state.pop(1);

    std::map< std::string, lutok::cxx_function > module;
    module["multiply"] = native_multiply;
    lutok::create_module(state, "native", module);
    ++checks;

    const unsigned int results2 = lutok::do_string(
        state, "return native.multiply(6, 7)", 0, 1, 0);
    if (results2 != 1 || state.to_integer(-1) != 42) {
        std::cerr << "native module call failed\n";
        return EXIT_FAILURE;
    }
    ++checks;
    state.pop(1);

    {
        lutok::stack_cleaner cleaner(state);
        state.push_integer(123);
        ++checks;
    }

    bool raised = false;
    try {
        lutok::do_string(state, "error('boom')", 0, 0, 0);
    } catch (const lutok::error&) {
        raised = true;
        ++checks;
    }
    if (!raised) {
        std::cerr << "lutok::error was not raised for a failing script\n";
        return EXIT_FAILURE;
    }

    lua_State* raw = lutok::state_c_gate(state).c_state();
    if (raw == nullptr) {
        std::cerr << "state_c_gate did not expose the raw lua_State\n";
        return EXIT_FAILURE;
    }
    ++checks;

    std::cout << "test_lutok: " << checks << " checks passed\n";
    return EXIT_SUCCESS;
}
