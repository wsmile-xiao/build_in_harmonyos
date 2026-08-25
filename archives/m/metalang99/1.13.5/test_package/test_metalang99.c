// test_package/test_metalang99.c — R34: substantive consumer test.
//
// Exercises the public metalang99 macro API across multiple functional
// areas (version, naturals, bool, tuple, either, maybe, list, util).
// Every ML99_ASSERT_* below expands to _Static_assert (C11), so a clean
// compile *is* a passing test — the same contract used by upstream's
// own tests/*.c. Failure to compile = a real assertion failure.
//
// Functional points covered:
//   1. ML99_VERSION_COMPATIBLE / ML99_VERSION_EQ  (version semantics)
//   2. ML99_inc / ML99_dec / ML99_add / ML99_sub  (Peano naturals)
//   3. ML99_natEq / ML99_natMatch                 (natural equality/match)
//   4. ML99_true / ML99_false / ML99_not / ML99_and / ML99_or / ML99_if (bool)
//   5. ML99_tuple / ML99_tupleCount / ML99_tupleGet / ML99_tupleIsSingle  (tuples)
//   6. ML99_isLeft / ML99_isRight / ML99_eitherEq / ML99_unwrapLeft  (either)
//   7. ML99_isJust / ML99_isNothing / ML99_maybeEq / ML99_maybeUnwrap (maybe)
//   8. ML99_list / ML99_cons / ML99_nil / ML99_listEq / ML99_isNil  (lists)
//   9. ML99_id / ML99_const / ML99_compose / ML99_cat             (util)
#include <metalang99.h>
#include <metalang99/assert.h>

int main(void) {

    // ── 1. Version semantics ─────────────────────────────────────────
    // metalang99.h defines ML99_MAJOR=1 ML99_MINOR=13 ML99_PATCH=5
    ML99_ASSERT_UNEVAL(ML99_VERSION_EQ(1, 13, 5));
    ML99_ASSERT_UNEVAL(ML99_VERSION_COMPATIBLE(1, 0, 0));
    ML99_ASSERT_UNEVAL(ML99_VERSION_COMPATIBLE(1, 13, 0));
    ML99_ASSERT_UNEVAL(ML99_VERSION_COMPATIBLE(1, 13, 5));
    ML99_ASSERT_UNEVAL(!ML99_VERSION_COMPATIBLE(2, 0, 0));
    ML99_ASSERT_UNEVAL(!ML99_VERSION_COMPATIBLE(1, 14, 0));
    ML99_ASSERT_UNEVAL(!ML99_VERSION_COMPATIBLE(1, 13, 6));

    // ── 2. Peano naturals: inc / dec / add / sub ─────────────────────
    ML99_ASSERT_EQ(ML99_inc(v(0)), v(1));
    ML99_ASSERT_EQ(ML99_inc(v(15)), v(16));
    ML99_ASSERT_EQ(ML99_dec(v(1)), v(0));
    ML99_ASSERT_EQ(ML99_dec(v(99)), v(98));
    ML99_ASSERT_EQ(ML99_add(v(3), v(4)), v(7));
    ML99_ASSERT_EQ(ML99_sub(v(10), v(6)), v(4));

    // ── 3. Natural equality & match ──────────────────────────────────
    ML99_ASSERT_EQ(ML99_natEq(v(5), v(5)), v(1));
    ML99_ASSERT_EQ(ML99_natEq(v(5), v(6)), v(0));

#define MATCH_Z_IMPL(...) v(88)
#define MATCH_S_IMPL(x)   v(x)
    ML99_ASSERT_EQ(ML99_natMatch(v(0), v(MATCH_)), v(88));
    ML99_ASSERT_EQ(ML99_natMatch(v(7), v(MATCH_)), v(6));
#undef MATCH_Z_IMPL
#undef MATCH_S_IMPL

    // ── 4. Bool algebra ──────────────────────────────────────────────
    ML99_ASSERT_EQ(ML99_true(), v(1));
    ML99_ASSERT_EQ(ML99_false(), v(0));
    ML99_ASSERT_EQ(ML99_not(v(0)), v(1));
    ML99_ASSERT_EQ(ML99_not(v(1)), v(0));
    ML99_ASSERT_EQ(ML99_and(v(1), v(1)), v(1));
    ML99_ASSERT_EQ(ML99_and(v(1), v(0)), v(0));
    ML99_ASSERT_EQ(ML99_or(v(0), v(1)), v(1));
    ML99_ASSERT_EQ(ML99_or(v(0), v(0)), v(0));
    ML99_ASSERT_EQ(ML99_if(ML99_true(), v(123), v(18)), v(123));
    ML99_ASSERT_EQ(ML99_if(ML99_false(), v(123), v(18)), v(18));

    // ── 5. Tuples ────────────────────────────────────────────────────
    ML99_ASSERT_EQ(ML99_tupleCount(v((1, 2, 3))), v(3));
    ML99_ASSERT_EQ(ML99_tupleCount(v((*))), v(1));
    ML99_ASSERT(ML99_not(ML99_tupleIsSingle(v((1, 2, 3)))));
    ML99_ASSERT(ML99_tupleIsSingle(v((9))));
    // ML99_tupleGet(i) returns a metafunction; apply it to a tuple term.
    ML99_ASSERT_EQ(ML99_tupleGet(0)(v((19, 8))), v(19));
    ML99_ASSERT_EQ(ML99_tupleGet(1)(v((19, 8))), v(8));
    ML99_ASSERT_EQ(ML99_tupleGet(2)(v((19, 8, 7378))), v(7378));
    // ML99_tuple + ML99_untuple round-trip.
    ML99_ASSERT_EQ(ML99_untuple(ML99_tuple(v(187))), v(187));

    // ── 6. Either (sum type) ─────────────────────────────────────────
    ML99_ASSERT_EQ(ML99_isLeft(ML99_left(v(123))), v(1));
    ML99_ASSERT_EQ(ML99_isLeft(ML99_right(v(123))), v(0));
    ML99_ASSERT_EQ(ML99_isRight(ML99_right(v(123))), v(1));
    ML99_ASSERT_EQ(ML99_isRight(ML99_left(v(123))), v(0));
    ML99_ASSERT(
        ML99_eitherEq(v(ML99_natEq), ML99_left(v(123)), ML99_left(v(123))));
    ML99_ASSERT(
        ML99_not(ML99_eitherEq(v(ML99_natEq), ML99_left(v(123)), ML99_right(v(123)))));
    ML99_ASSERT_EQ(ML99_unwrapLeft(ML99_left(v(42))), v(42));
    ML99_ASSERT_EQ(ML99_unwrapRight(ML99_right(v(42))), v(42));

    // ── 7. Maybe ─────────────────────────────────────────────────────
    ML99_ASSERT(ML99_isJust(ML99_just(v(9))));
    ML99_ASSERT(ML99_not(ML99_isJust(ML99_nothing())));
    ML99_ASSERT(ML99_isNothing(ML99_nothing()));
    ML99_ASSERT(ML99_not(ML99_isNothing(ML99_just(v(9)))));
    ML99_ASSERT(
        ML99_maybeEq(v(ML99_natEq), ML99_just(v(7)), ML99_just(v(7))));
    ML99_ASSERT(
        ML99_not(ML99_maybeEq(v(ML99_natEq), ML99_just(v(7)), ML99_nothing())));
    ML99_ASSERT_EQ(ML99_maybeUnwrap(ML99_just(v(123))), v(123));

    // ── 8. Lists ─────────────────────────────────────────────────────
    ML99_ASSERT(ML99_isNil(ML99_nil()));
    ML99_ASSERT(ML99_isNil(ML99_nil(v(~, ~, ~))));
    ML99_ASSERT(ML99_listEq(
        v(ML99_natEq),
        ML99_list(v(1, 2, 3, 4, 5, 6, 7)),
        ML99_cons(
            v(1),
            ML99_cons(
                v(2),
                ML99_cons(
                    v(3),
                    ML99_cons(
                        v(4),
                        ML99_cons(v(5), ML99_cons(v(6), ML99_cons(v(7), ML99_nil())))))))));

    // ── 9. Util: id / const / compose / cat ──────────────────────────
    ML99_ASSERT_EQ(ML99_appl(ML99_compose(v(ML99_id), v(ML99_id)), v(181)),
                   v(181));
    ML99_ASSERT_EQ(ML99_appl2(v(ML99_const), v(1810), v(~)), v(1810));
    ML99_ASSERT_EQ(ML99_cat(v(12), v(345)), v(12345));
    ML99_ASSERT_UNEVAL(ML99_CAT(12, 345) == 12345);

    return 0;
}
