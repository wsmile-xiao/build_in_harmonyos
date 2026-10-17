// test_soplex.cpp — Conan consumer test for SoPlex 7.1.6
//
// Builds a small LP through the public SoPlex C++ API, solves it and
// verifies the optimal objective value. Based on the upstream
// example shipped in the SoPlex source (src/example.cpp).
#include <cstdlib>
#include <iostream>

#include "soplex.h"

using namespace soplex;

int main()
{
   SoPlex mysoplex;

   /* set the objective sense */
   mysoplex.setIntParam(SoPlex::OBJSENSE, SoPlex::OBJSENSE_MINIMIZE);

   /* we first add variables */
   DSVector dummycol(0);
   mysoplex.addColReal(LPCol(2.0, dummycol, infinity, 15.0));
   mysoplex.addColReal(LPCol(3.0, dummycol, infinity, 20.0));

   /* then constraints one by one */
   DSVector row1(2);
   row1.add(0, 1.0);
   row1.add(1, 5.0);
   mysoplex.addRowReal(LPRow(100.0, row1, infinity));

   /* solve LP */
   SPxSolver::Status stat = mysoplex.optimize();

   if(stat != SPxSolver::OPTIMAL)
   {
      std::cerr << "FAIL: solve did not reach optimality (status=" << stat << ")\n";
      return 1;
   }

   /* LP: min 2*x0 + 3*x1  s.t.  x0 + 5*x1 >= 100,  x0 >= 15,  x1 >= 20
      LPCol(obj, col, upper, lower): x0 lower=15 (unbounded above),
      x1 lower=20 -> constraint auto-satisfied, optimum at x0=15, x1=20
      -> objective = 2*15 + 3*20 = 90 */
   const Real obj = mysoplex.objValueReal();
   const Real expected = 90.0;
   const bool ok = (obj >= expected - 1e-6) && (obj <= expected + 1e-6);

   std::cout << "SoPlex solved LP to optimality, objective = " << obj << "\n";

   if(!ok)
   {
      std::cerr << "FAIL: objective " << obj << " != expected " << expected << "\n";
      return 1;
   }

   std::cout << "test_soplex: PASS\n";
   return 0;
}
