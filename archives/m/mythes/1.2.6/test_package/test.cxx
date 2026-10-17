#include <mythes.hxx>
#include <cstdio>
#include <cstring>

int main(int argc, char **argv) {
    if (argc != 3)
        return 2;
    MyThes thes(argv[1], argv[2]);
    if (std::strcmp(thes.get_th_encoding(), "UTF-8") != 0)
        return 3;
    mentry *meanings = nullptr;
    int count = thes.Lookup("cloud", 5, &meanings);
    if (count != 1 || !meanings || meanings[0].count != 2 ||
        std::strcmp(meanings[0].psyns[0], "vapor") != 0 ||
        std::strcmp(meanings[0].psyns[1], "mist") != 0)
        return 4;
    thes.CleanUpAfterLookup(&meanings, count);
    if (meanings != nullptr)
        return 5;
    if (thes.Lookup("absent", 6, &meanings) != 0 || meanings != nullptr)
        return 6;
    std::puts("mythes installed-consumer lookup: PASS");
    return 0;
}
