/* C++ frontend + libstdc++ smoke: exercises std::string, std::vector and
 * std::printf so the linked ELF must carry libstdc++ machinery (basic_string,
 * vector, new/delete) resolved from the packaged toolchain.  */
#include <cstdio>
#include <string>
#include <vector>

int main()
{
    std::string s = "cpp-ok";
    std::vector<int> v;
    v.push_back(7);
    v.push_back(3);
    std::size_t sum = 0;
    for (std::vector<int>::const_iterator it = v.begin(); it != v.end(); ++it)
        sum += static_cast<std::size_t>(*it);
    std::printf("%s %zu %zu\n", s.c_str(), s.size(), sum);
    return (s.size() == 6 && sum == 10) ? 0 : 1;
}
