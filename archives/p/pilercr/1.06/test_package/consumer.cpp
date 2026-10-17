#include "discovered.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

// The header is generated from the packaged OHOS tool's actual FASTA report.
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    std::ifstream report(argv[1]);
    if (!report) return 3;
    std::string line;
    bool in_position_summary = false;
    int matches = 0;
    while (std::getline(report, line)) {
        if (line == "SUMMARY BY SIMILARITY") in_position_summary = true;
        if (line == "SUMMARY BY POSITION") in_position_summary = false;
        if (!in_position_summary) continue;
        std::istringstream row(line);
        int array, position, length, copies, repeat_length, spacer_length;
        std::string name, strand, consensus;
        if (row >> array >> name >> position >> length >> copies >> repeat_length
                >> spacer_length >> strand >> consensus && array == 1 && name == "ohos_pc_crispr" && strand == "+") {
            if (position != DETECTED_POSITION || copies != DETECTED_COPIES ||
                consensus != DETECTED_REPEAT || length < 300 || repeat_length < 16 ||
                spacer_length < 8) return 4;
            ++matches;
        }
    }
    if (matches != 1 || DETECTED_POSITION != 401 || DETECTED_COPIES < 3) return 5;
    std::cout << "OHOS pilercr consumer PASS: array at " << DETECTED_POSITION
              << ", " << DETECTED_COPIES << " repeats, consensus "
              << DETECTED_REPEAT << '\n';
    return 0;
}
