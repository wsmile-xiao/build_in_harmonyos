/*
 * test_package/test.c — libcello 2.1.0 consumer-side L1 test.
 *
 * Includes <Cello.h>, links libCello.a + -lpthread + -lm (matching the
 * upstream Makefile Linux link line), and exercises core objects /
 * containers / exceptions with REAL value + lifetime assertions. This is
 * not a compile-only stub: every check returns non-zero on mismatch.
 *
 * Cello redefines `main` (in Cello.h) to bootstrap the GC and call
 * Cello_Main, so the user entry point must keep the canonical
 * `int main(int argc, char** argv)` signature.
 */
#include <Cello.h>
#include <stdio.h>
#include <string.h>

/* A custom exception type (same idiom as upstream tests/test.c). */
static var BoomError = CelloEmpty(BoomError);

/* Lightweight assert that prints and returns 1 on failure so the process
 * exits non-zero (CI catches non-zero). 0 = pass. */
#define CHECK(cond, ...)                                                       \
  do {                                                                         \
    if (!(cond)) {                                                             \
      printf("FAIL: " __VA_ARGS__);                                            \
      printf(" (%s:%d)\n", __FILE__, __LINE__);                               \
      return 1;                                                                \
    }                                                                          \
  } while (0)

int main(int argc, char** argv) {

  /* ── 1. Primitive objects: Int / Float value + equality ─────────── */
  var x = new(Int, $I(42));
  var y = new(Int, $I(42));
  CHECK(cmp(x, y) == 0, "Int 42 == 42 cmp");
  CHECK(eq(x, $I(42)), "Int 42 eq $I(42)");
  CHECK(cmp(x, $I(7)) > 0, "Int 42 > 7");
  CHECK(cmp(x, $I(100)) < 0, "Int 42 < 100");

  var f = new(Float, $F(3.14));
  CHECK(eq(f, $F(3.14)), "Float 3.14 eq");
  CHECK(not eq(f, $F(2.71)), "Float 3.14 != 2.71");
  CHECK(c_float(f) == 3.14, "c_float == 3.14");
  CHECK(c_int(x) == 42, "c_int == 42");
  del(x); del(y); del(f);

  /* ── 2. String: construct / value / lifetime ─────────────────────── */
  var s = new(String, $S("Hello"));
  CHECK(eq(s, $S("Hello")), "String == Hello");
  CHECK(len(s) == 5, "String len 5");

  /* copy produces an independent object with equal value */
  var s2 = copy(s);
  CHECK(s isnt s2, "String copy is distinct object");
  CHECK(eq(s, s2), "String copy equal value");
  del(s2);

  /* assign mutates in place */
  assign(s, $S("World"));
  CHECK(eq(s, $S("World")), "String assign World");
  CHECK(not eq(s, $S("Hello")), "String assign changed value");
  CHECK(strcmp(c_str(s), "World") == 0, "c_str == World");
  del(s);

  /* ── 3. Array: indexed container, lifetime, sort, iter ───────────── */
  var a = new(Array, Int, $I(5), $I(3), $I(1), $I(4), $I(2));
  CHECK(len(a) == 5, "Array len 5");
  CHECK(eq(get(a, $I(0)), $I(5)), "Array[0]==5");
  CHECK(eq(get(a, $I(4)), $I(2)), "Array[4]==2");

  /* sort() ascending; sort_by(a, gt) descending (upstream idiom) */
  var a_asc = copy(a);
  sort(a_asc);
  CHECK(eq(get(a_asc, $I(0)), $I(1)), "Array sorted[0]==1");
  CHECK(eq(get(a_asc, $I(4)), $I(5)), "Array sorted[4]==5");

  var a_desc = copy(a);
  sort_by(a_desc, gt);
  CHECK(eq(get(a_desc, $I(0)), $I(5)), "Array sort_by gt[0]==5");
  CHECK(eq(get(a_desc, $I(4)), $I(1)), "Array sort_by gt[4]==1");

  /* mutation: push / pop */
  push(a, $I(99));
  CHECK(eq(get(a, $I(5)), $I(99)), "Array push 99");
  CHECK(len(a) == 6, "Array len 6 after push");
  pop(a);
  CHECK(len(a) == 5, "Array pop back to 5");

  /* iteration sum via foreach */
  long sum = 0;
  foreach (item in a) {
    sum += c_int(item);
  }
  CHECK(sum == 15, "Array iter sum==15 (5+3+1+4+2)");
  del(a); del(a_asc); del(a_desc);

  /* ── 4. List: linked list, iter, lifetime ────────────────────────── */
  var l = new(List, Int, $I(10), $I(20), $I(30));
  CHECK(len(l) == 3, "List len 3");
  CHECK(eq(get(l, $I(0)), $I(10)), "List[0]==10");
  CHECK(eq(get(l, $I(2)), $I(30)), "List[2]==30");

  long lsum = 0;
  foreach (item in l) {
    lsum += c_int(item);
  }
  CHECK(lsum == 60, "List iter sum==60 (10+20+30)");
  del(l);

  /* ── 5. Table (hash map): set/get/rem/lifetime ────────────────────── */
  var t = new(Table, String, Int);
  set(t, $S("one"),   $I(1));
  set(t, $S("two"),   $I(2));
  set(t, $S("three"), $I(3));
  CHECK(len(t) == 3, "Table len 3");
  CHECK(eq(get(t, $S("two")), $I(2)), "Table[two]==2");
  CHECK(eq(get(t, $S("one")), $I(1)), "Table[one]==1");
  CHECK(mem(t, $S("three")) == true, "Table mem three");
  rem(t, $S("two"));
  CHECK(len(t) == 2, "Table len 2 after rem");
  CHECK(mem(t, $S("two")) == false, "Table !mem two after rem");
  del(t);

  /* ── 6. Tree (balanced map): set/get/lifetime ────────────────────── */
  var tr = new(Tree, Int, String);
  set(tr, $I(1), $S("a"));
  set(tr, $I(3), $S("c"));
  set(tr, $I(2), $S("b"));
  CHECK(len(tr) == 3, "Tree len 3");
  CHECK(eq(get(tr, $I(2)), $S("b")), "Tree[2]==b");
  CHECK(eq(get(tr, $I(3)), $S("c")), "Tree[3]==c");
  del(tr);

  /* ── 7. Tuple: fixed heterogeneous sequence + lifetime ──────────── */
  var tup = new(Tuple, $I(7), $S("eight"), $F(9.0));
  CHECK(len(tup) == 3, "Tuple len 3");
  CHECK(eq(get(tup, $I(0)), $I(7)), "Tuple[0]==7");
  CHECK(eq(get(tup, $I(1)), $S("eight")), "Tuple[1]==eight");
  del(tup);

  /* ── 8. Range + iter: functional range iteration ────────────────── */
  long cnt = 0;
  foreach (_ in range($I(5))) { cnt++; }
  CHECK(cnt == 5, "range(5) yields 5");

  /* ── 9. Exception: try/catch/throw with real control flow ────────── */
  bool caught = false;
  try {
    throw(BoomError, "boom");
  } catch (e in BoomError) {
    caught = true;
  }
  CHECK(caught, "Exception thrown and caught");
  CHECK(len(current(Exception)) is 0, "Exception depth 0 after catch");

  /* catch-all also works */
  bool caught_all = false;
  try {
    throw(BoomError, "again");
  } catch (e) {
    caught_all = true;
  }
  CHECK(caught_all, "Exception catch-all");

  /* ── 10. Copy semantics + GC registration ─────────────────────────── */
  var orig = new(String, $S("orig"));
  var dup = copy(orig);
  CHECK(eq(orig, dup), "copy equal value");
  CHECK(orig isnt dup, "copy distinct identity");
  assign(dup, $S("changed"));
  CHECK(eq(orig, $S("orig")), "original unchanged after copy mutate");
  del(orig); del(dup);

  printf("All Cello consumer checks passed (10 groups).\n");
  return 0;
}
