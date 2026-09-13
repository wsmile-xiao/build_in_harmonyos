#include <cstdio>
#include <cstdlib>
#include <cmath>

// Vol public API (installed to <prefix>/include/coin)
#include "VolVolume.hpp"

// Minimal real user hook: solves a trivial one-variable subproblem so the
// volume algorithm actually iterates and produces primal/dual solutions.
class TinyHook : public VOL_user_hooks {
public:
   virtual int compute_rc(const VOL_dvector& u, VOL_dvector& rc) {
      // rc = c - A^T u with A = [1], c = 0
      rc[0] = -u[0];
      return 0;
   }
   virtual int solve_subproblem(const VOL_dvector& dual, const VOL_dvector& rc,
                                double& lcost, VOL_dvector& x, VOL_dvector& v,
                                double& pcost) {
      const double b = 1.0;               // rhs of the single row
      x[0] = (rc[0] >= 0.0) ? 0.0 : 1.0;  // x in {0,1} chosen by reduced cost
      lcost = b * dual[0] + x[0] * rc[0];
      v[0] = b - x[0];                    // b - A x
      pcost = 0.0;                        // objective c^T x = 0
      return 0;
   }
   virtual int heuristics(const VOL_problem& p, const VOL_dvector& x,
                          double& heur_val) {
      heur_val = 0.0;
      return 0;
   }
};

int main(void) {
   VOL_problem volprob;
   volprob.dsize = 1;
   volprob.psize = 1;
   volprob.dual_lb.allocate(1);
   volprob.dual_ub.allocate(1);
   volprob.dual_lb[0] = -1.0e31;
   volprob.dual_ub[0] = 1.0e31;
   // Limit iterations so the test terminates fast
   volprob.parm.maxsgriters = 50;

   TinyHook hook;
   const int rc = volprob.solve(hook, false);

   if (rc != 0) {
      printf("coinor-vol consumer test FAILED: solve rc=%d\n", rc);
      return 1;
   }
   if (volprob.psol.size() != 1 || volprob.dsol.size() != 1) {
      printf("coinor-vol consumer test FAILED: solution vectors missing\n");
      return 1;
   }
   printf("coinor-vol consumer test OK: value=%.6f dsol[0]=%.6f\n",
          volprob.value, volprob.dsol[0]);
   return 0;
}