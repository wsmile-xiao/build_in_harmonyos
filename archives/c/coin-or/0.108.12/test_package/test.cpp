// test_package for coin-or 0.108.12 (COIN-OR Osi)
// R34: substantive test — actually calls the Osi API (OsiCuts/OsiRowCut)
#include <coin/OsiCuts.hpp>
#include <coin/OsiRowCut.hpp>

int main() {
    // Exercise the Osi cuts API (concrete classes shipped in libOsi)
    OsiCuts cuts;
    OsiRowCut rc;
    rc.setLb(-1.0);
    rc.setUb(1.0);
    cuts.insert(rc);

    if (cuts.sizeRowCuts() != 1) {
        return 1;
    }
    const OsiRowCut &got = cuts.rowCut(0);
    if (got.lb() != -1.0 || got.ub() != 1.0) {
        return 2;
    }
    return 0;
}
