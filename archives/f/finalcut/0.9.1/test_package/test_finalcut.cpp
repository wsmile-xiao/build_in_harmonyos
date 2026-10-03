#include <final/final.h>

#include <string>

int main()
{
    const finalcut::FString text("Final Cut");
    if (text.getLength() != 9)
        return 1;
    if (text.toString() != std::string("Final Cut"))
        return 2;

    return 0;
}
