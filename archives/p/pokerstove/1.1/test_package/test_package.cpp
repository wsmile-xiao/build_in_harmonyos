// test_package.cpp — pokerstove 1.1 consumer test (R34: real API usage)
//
// Links the packaged peval + penum libraries and exercises the real
// evaluation pipeline:
//   1. Card / CardSet parsing (string -> card representation)
//   2. HoldemHandEvaluator (7-card hand evaluation, AcAs vs Kh4d on 5c8s9h)
//   3. ShowdownEnumerator::calculateEquity (full equity enumeration,
//      assert the canonical value: AcAs = 967/990 = 97.6768% equity
//      vs Kh4d on board 5c8s9h)
#include <pokerstove/peval/Card.h>
#include <pokerstove/peval/CardSet.h>
#include <pokerstove/peval/HoldemHandEvaluator.h>
#include <pokerstove/penum/CardDistribution.h>
#include <pokerstove/penum/ShowdownEnumerator.h>

#include <cmath>
#include <iostream>
#include <string>
#include <vector>

using namespace pokerstove;

static int failures = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        if (cond) {                                                   \
            std::cout << "[PASS] " << msg << std::endl;               \
        } else {                                                      \
            std::cout << "[FAIL] " << msg << std::endl;               \
            ++failures;                                               \
        }                                                             \
    } while (0)

int main()
{
    // ── 1. Card / CardSet parsing ──────────────────────────────────
    Card aceClubs("Ac");
    CHECK(aceClubs.rank() == Rank::Ace(), "Card(Ac).rank() == Ace");
    CHECK(aceClubs.str() == "Ac", "Card(Ac).str() == Ac");

    CardSet hole("AcAs");
    CHECK(hole.size() == 2, "CardSet(AcAs).size() == 2");
    CHECK(hole.str() == "AcAs", "CardSet(AcAs).str() == AcAs");

    CardSet board("5c8s9h");
    CHECK(board.size() == 3, "CardSet(5c8s9h).size() == 3");

    // ── 2. Hand evaluation through HoldemHandEvaluator ─────────────
    boost::shared_ptr<PokerHandEvaluator> evaluator = PokerHandEvaluator::alloc("h");
    CHECK(evaluator->handSize() == 2, "holdem evaluator handSize() == 2");

    PokerEvaluation evAa = evaluator->evaluateHand(hole, board).high();
    PokerEvaluation evK4 = evaluator->evaluateHand(CardSet("Kh4d"), board).high();
    std::cout << "AcAs on 5c8s9h -> " << evAa.str()
              << " (code " << evAa.code() << ")" << std::endl;
    std::cout << "Kh4d on 5c8s9h -> " << evK4.str()
              << " (code " << evK4.code() << ")" << std::endl;
    CHECK(evAa.code() > evK4.code(), "AcAs evaluates higher than Kh4d on 5c8s9h");

    // ── 3. Equity enumeration (ShowdownEnumerator) ─────────────────
    std::vector<CardDistribution> handDists;
    handDists.emplace_back();
    handDists.back().parse("AcAs");
    handDists.emplace_back();
    handDists.back().parse("Kh4d");

    ShowdownEnumerator showdown;
    std::vector<EquityResult> results =
        showdown.calculateEquity(handDists, board, evaluator);

    CHECK(results.size() == 2, "calculateEquity returned 2 results");

    double total = 0.0;
    for (const EquityResult& r : results)
        total += r.winShares + r.tieShares;

    double eqAa = (results[0].winShares + results[0].tieShares) / total;
    double eqK4 = (results[1].winShares + results[1].tieShares) / total;
    std::cout << "AcAs equity: " << eqAa * 100.0 << "% (" << results[0].str() << ")" << std::endl;
    std::cout << "Kh4d equity: " << eqK4 * 100.0 << "% (" << results[1].str() << ")" << std::endl;

    // canonical value: (959 wins + 8 ties) / 990 boards = 967/990
    CHECK(std::fabs(eqAa - 967.0 / 990.0) < 1e-9,
          "AcAs equity == 967/990 (97.6768%) vs Kh4d on 5c8s9h");
    CHECK(std::fabs(eqK4 - 23.0 / 990.0) < 1e-9,
          "Kh4d equity == 23/990 (2.32323%) vs AcAs on 5c8s9h");
    CHECK(std::fabs(eqAa + eqK4 - 1.0) < 1e-9, "equities sum to 1");

    // ── summary ────────────────────────────────────────────────────
    if (failures == 0) {
        std::cout << "ALL TESTS PASSED" << std::endl;
        return 0;
    }
    std::cout << failures << " TESTS FAILED" << std::endl;
    return 1;
}
