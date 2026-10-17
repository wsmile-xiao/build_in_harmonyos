#include <cstdlib>
#include <iostream>
#include <string>

#include "motti/Board.h"
#include "motti/Case.h"
#include "motti/Player.h"

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (cond) { std::cout << "PASS: " << (msg) << std::endl; } \
    else { std::cout << "FAIL: " << (msg) << std::endl; failures++; } \
} while (0)

/*
 * Consumer test: links libmottifram and exercises the public Board/Case/Player
 * API the way a library user would, deciding the exit code from real
 * behavioural assertions.
 */
int main()
{
    /* 1. board dimensions */
    Board board(10, 10);
    CHECK(board.getWidth() == 10 && board.getHeight() == 10,
          "Board(10,10) reports width=10 height=10");

    /* 2. case attributes survive set/read */
    Player player("Tester");
    Case city(true, &player, Case::SELECTED);
    CHECK(city.isCityCenter() && city.getType() == Case::SELECTED &&
          city.getPlayer() == &player,
          "Case(bool,Player*,CASETYPE) getters round-trip");

    /* 3. setCase + getCaseNoThrow read-back */
    board.setCase(5, 5, city);
    Case *got = board.getCaseNoThrow(5, 5);
    CHECK(got != nullptr && got->isCityCenter() &&
          got->getType() == Case::SELECTED,
          "getCaseNoThrow(5,5) returns the case set via setCase");

    /* 4. out-of-range access returns nullptr without throwing */
    Case *oob = board.getCaseNoThrow(99, 99);
    CHECK(oob == nullptr, "getCaseNoThrow(99,99) returns nullptr");

    /* 5. JSON export mentions the board size fields */
    std::string json = board.generateJson();
    CHECK(json.find("\"xsize\":10") != std::string::npos &&
          json.find("\"ysize\":10") != std::string::npos,
          "generateJson() contains xsize/ysize 10");

    /* 6. another board size via the int constructor */
    Board small(4, 7);
    CHECK(small.getWidth() == 4 && small.getHeight() == 7,
          "Board(4,7) reports width=4 height=7");

    /* 7. case type setter round-trip */
    Case freeCase;
    freeCase.setCaseType(Case::LOCKED);
    CHECK(freeCase.getType() == Case::LOCKED,
          "Case::setCaseType(LOCKED) round-trips via getType");

    /* 8. case JSON export is non-empty */
    CHECK(!city.generateJson().empty(), "Case::generateJson() non-empty");

    if (failures == 0) {
        std::cout << "motti consumer test: all 8 checks passed" << std::endl;
        return 0;
    }
    std::cout << "motti consumer test: " << failures << "/8 checks FAILED"
              << std::endl;
    return 1;
}
