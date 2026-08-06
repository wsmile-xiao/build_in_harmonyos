// Conan L1 test for aiksaurus — real synonym lookup against package data.
//
// Usage: test_aiksaurus <meanings.dat> <words.dat>
// Exercises the Aiksaurus C++ API: find() + next().
#include <Aiksaurus.h>
#include <cstdio>
#include <cstring>
#include <string>

int main(int argc, char** argv)
{
    if (argc < 3) {
        std::fprintf(stderr, "usage: %s <meanings.dat> <words.dat>\n", argv[0]);
        return 2;
    }

    try {
        Aiksaurus thes(argv[1], argv[2]);
        if (thes.error()[0]) {
            std::fprintf(stderr, "aiksaurus init error: %s\n", thes.error());
            return 1;
        }

        // "happy" is a well-known word in the bundled thesaurus.
        if (!thes.find("happy")) {
            std::fprintf(stderr, "find('happy') returned false\n");
            return 1;
        }
        if (std::strcmp(thes.word(), "happy") != 0) {
            std::fprintf(stderr, "word() mismatch: %s\n", thes.word());
            return 1;
        }

        // Walk the first meaning and require at least one synonym.
        int meaning = 0;
        int syn_count = 0;
        const char* syn;
        while ((syn = thes.next(meaning))[0]) {
            ++syn_count;
            if (syn_count > 200) {
                break;  // guard against pathological loops
            }
        }
        if (syn_count == 0) {
            std::fprintf(stderr, "no synonyms returned for 'happy'\n");
            return 1;
        }

        std::printf("aiksaurus OK: 'happy' -> %d synonyms (meanings=%d)\n",
                    syn_count, meaning);
        return 0;
    }
    catch (...) {
        std::fprintf(stderr, "aiksaurus threw unexpected exception\n");
        return 1;
    }
}
