#include <link-grammar/link-includes.h>

#include <cstdio>
#include <cstring>

int main(int argc, char **argv)
{
    if (argc != 2 || argv[1][0] == '\0') {
        std::fprintf(stderr, "usage: %s <dictionary-directory>\n", argv[0]);
        return 1;
    }

    dictionary_set_data_dir(argv[1]);

    const char *version = linkgrammar_get_version();
    if (version == nullptr ||
        std::strcmp(version, "link-grammar-5.13.0") != 0) {
        std::fprintf(stderr, "unexpected version: %s\n", version ? version : "null");
        return 2;
    }

    Dictionary dictionary = dictionary_create_lang("en");
    if (dictionary == nullptr) {
        std::fprintf(stderr, "failed to load the English dictionary from %s\n", argv[1]);
        return 3;
    }

    Parse_Options options = parse_options_create();
    Sentence sentence = sentence_create("This is a test.", dictionary);
    if (options == nullptr || sentence == nullptr) {
        std::fprintf(stderr, "failed to create parser objects\n");
        sentence_delete(sentence);
        parse_options_delete(options);
        dictionary_delete(dictionary);
        return 4;
    }

    const int linkage_count = sentence_parse(sentence, options);
    if (linkage_count <= 0 || sentence_num_valid_linkages(sentence) <= 0) {
        std::fprintf(stderr, "sentence parsing produced no valid linkage\n");
        sentence_delete(sentence);
        parse_options_delete(options);
        dictionary_delete(dictionary);
        return 5;
    }

    Linkage linkage = linkage_create(0, sentence, options);
    if (linkage == nullptr || linkage_get_num_words(linkage) < 4 ||
        linkage_get_num_links(linkage) == 0) {
        std::fprintf(stderr, "unexpected linkage structure\n");
        linkage_delete(linkage);
        sentence_delete(sentence);
        parse_options_delete(options);
        dictionary_delete(dictionary);
        return 6;
    }

    std::printf("Link Grammar %s parsed the sentence with %d linkage(s)\n",
                version, linkage_count);
    linkage_delete(linkage);
    sentence_delete(sentence);
    parse_options_delete(options);
    dictionary_delete(dictionary);
    return 0;
}
