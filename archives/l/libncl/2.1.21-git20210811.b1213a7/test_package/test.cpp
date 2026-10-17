#include "ncl/nxsmultiformat.h"
#include "ncl/nxspublicblocks.h"

#include <iostream>
#include <stdexcept>
#include <string>

static void check(bool condition, const char *message)
{
    if (!condition)
        throw std::runtime_error(message);
    std::cout << "PASS " << message << '\n';
}

int main(int argc, char **argv)
{
    if (argc != 3)
    {
        std::cerr << "usage: test_ncl characters.nex somebrlens.nex\n";
        return 2;
    }
    try
    {
        MultiFormatReader characters(-1, NxsReader::WARNINGS_TO_STDERR);
        characters.ReadFilepath(argv[1], MultiFormatReader::NEXUS_FORMAT);
        check(characters.GetNumTaxaBlocks() >= 1, "TAXA block parsed");
        NxsTaxaBlock *taxa = characters.GetTaxaBlock(0);
        check(taxa && taxa->GetNTax() == 6, "TAXA count is six");
        check(taxa->GetTaxonLabel(0) == "P. fimbriata", "quoted taxon label parsed");
        check(characters.GetNumCharactersBlocks(0) >= 1, "CHARACTERS block parsed");
        NxsCharactersBlock *matrix = characters.GetCharactersBlock(0, 0);
        check(matrix && matrix->GetNCharTotal() == 45, "CHARACTERS count is 45");
        check(matrix->IsMissingState(3, 35), "missing state preserved");

        MultiFormatReader trees(-1, NxsReader::WARNINGS_TO_STDERR);
        trees.ReadFilepath(argv[2], MultiFormatReader::NEXUS_FORMAT);
        check(trees.GetNumTaxaBlocks() >= 1 && trees.GetTaxaBlock(0)->GetNTax() == 4,
              "tree TAXA count is four");
        check(trees.GetNumTreesBlocks(0) >= 1, "TREES block parsed");
        NxsTreesBlock *tree_block = trees.GetTreesBlock(0, 0);
        check(tree_block && tree_block->GetNumTrees() == 1, "one tree parsed");
        check(tree_block->GetTreeName(0) == "t", "tree name preserved");
        std::cout << "LIBNCL_CONSUMER_PASS assertions=10\n";
        return 0;
    }
    catch (const NxsException &error)
    {
        std::cerr << "NCL parse error: " << error.msg << '\n';
    }
    catch (const std::exception &error)
    {
        std::cerr << "Consumer assertion failed: " << error.what() << '\n';
    }
    return 1;
}
