#include <adios2.h>

#include <array>
#include <cstdio>
#include <string>

int main()
{
    const std::string path = "adios2_test.bp";
    const std::array<int, 4> expected = {3, 5, 8, 13};

    adios2::ADIOS writerAdios;
    auto writerIO = writerAdios.DeclareIO("writer");
    auto variable = writerIO.DefineVariable<int>("values", {4}, {0}, {4});
    auto writer = writerIO.Open(path, adios2::Mode::Write);
    writer.Put(variable, expected.data());
    writer.Close();

    std::array<int, 4> actual = {};
    adios2::ADIOS readerAdios;
    auto readerIO = readerAdios.DeclareIO("reader");
    auto reader = readerIO.Open(path, adios2::Mode::ReadRandomAccess);
    auto input = readerIO.InquireVariable<int>("values");
    if (!input)
    {
        std::fprintf(stderr, "variable not found\n");
        return 1;
    }
    reader.Get(input, actual.data(), adios2::Mode::Sync);
    reader.Close();

    if (actual != expected)
    {
        std::fprintf(stderr, "round-trip mismatch\n");
        return 1;
    }

    std::puts("ADIOS2 BP round-trip passed");
    return 0;
}
