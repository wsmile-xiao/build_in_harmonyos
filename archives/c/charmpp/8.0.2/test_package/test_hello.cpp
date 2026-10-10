#include <stdio.h>
#include <stdlib.h>

#include "test_hello.decl.h"

/* readonly */ CProxy_Main mainProxy;
/* readonly */ int nElements;

/* mainchare */
class Main : public CBase_Main
{
public:
  Main(CkArgMsg *m)
  {
    nElements = 5;
    if (m->argc > 1)
      nElements = atoi(m->argv[1]);
    delete m;

    CkPrintf("Running Hello on %d processors for %d elements\n", CkNumPes(), nElements);
    mainProxy = thisProxy;

    CProxy_Hello arr = CProxy_Hello::ckNew(nElements);
    arr[0].SayHi(17);
  }

  void done(void)
  {
    CkPrintf("All done\n");
    CkExit();
  }
};

/* array [1D] */
class Hello : public CBase_Hello
{
public:
  Hello()
  {
    CkPrintf("[%d] Hello %d created\n", CkMyPe(), thisIndex);
  }

  Hello(CkMigrateMessage *m) {}

  void SayHi(int hiNo)
  {
    CkPrintf("[%d] Hi[%d] from element %d\n", CkMyPe(), hiNo, thisIndex);
    if (thisIndex < nElements - 1)
      thisProxy[thisIndex + 1].SayHi(hiNo + 1); /* pass the hello on */
    else
      mainProxy.done(); /* we have been around once */
  }
};

#include "test_hello.def.h"
