#include <flext.h>

#if !defined(FLEXT_VERSION) || (FLEXT_VERSION < 400)
#error You need at least flext version 0.4.0
#endif

// Minimal flext external used by the consumer test.  It reports its creation
// argument and the float-addition result through Pd's post(), and forwards the
// result to its outlet so [print] can also observe it.
class flextest : public flext_base {
    FLEXT_HEADER(flextest, flext_base)

public:
    explicit flextest(float init) : arg(init) {
        AddInAnything();
        AddOutFloat();
        FLEXT_ADDMETHOD(0, m_float);
        post("FLEXT_TEST_INIT: %g", (double)arg);
    }

protected:
    void m_float(float f) {
        float res = arg + f;
        post("FLEXT_TEST_RESULT: %g", (double)res);
        ToOutFloat(0, res);
    }

    float arg;

private:
    FLEXT_CALLBACK_F(m_float)
};

FLEXT_NEW_1("flextest", flextest, float)
