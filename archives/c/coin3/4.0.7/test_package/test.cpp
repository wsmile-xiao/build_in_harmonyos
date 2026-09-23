// test_package consumer test for coin3 4.0.7 on OHOS.
// Verifies a third-party consumer can compile, link, initialize the Coin
// library (Open Inventor 2.1 API) and exercise a real public API with an
// observable result: building a scene graph and writing it to an Inventor
// buffer that must contain the expected node type name.
#include <Inventor/SoDB.h>
#include <Inventor/SoInput.h>
#include <Inventor/SoOutput.h>
#include <Inventor/actions/SoWriteAction.h>
#include <Inventor/nodes/SoSeparator.h>
#include <Inventor/nodes/SoCube.h>

#include <cstdio>
#include <cstring>

int main(void) {
  // Public API: global init of the Coin database.
  SoDB::init();
  // Public API: build a small scene graph.
  SoSeparator * root = new SoSeparator;
  root->ref();
  SoCube * cube = new SoCube;
  cube->width.setValue(2.0f);
  root->addChild(cube);

  // Public API: write the scene graph into a caller-provided buffer; the
  // output must contain the "Cube" node type we created.
  char buf[4096];
  memset(buf, 0, sizeof(buf));
  SoOutput out;
  out.setBuffer(buf, sizeof(buf), 0);
  SoWriteAction wa(&out);
  wa.apply(root);

  void * outbuf = 0;
  size_t nbytes = 0;
  out.getBuffer(outbuf, nbytes);
  if (outbuf == 0 || nbytes == 0) {
    fprintf(stderr, "FAIL: scene write produced empty buffer\n");
    root->unref();
    return 1;
  }
  if (strstr(static_cast<const char *>(outbuf), "Cube") == 0) {
    fprintf(stderr, "FAIL: expected 'Cube' node in output, got:\n%s\n",
            static_cast<const char *>(outbuf));
    root->unref();
    return 1;
  }

  // Public API: cleanup — release the scene graph. SoDB::finish() is
  // intentionally not called: on OHOS it tears down the gl4es GL bridge
  // while gl4es is still shutting down its EGL context, which crashes in a
  // headless environment. The consumer verification (init, scene graph
  // build, write-back with observable content) is complete at this point.
  root->unref();

  printf("test coin3 4.0.7: OK (scene graph write verified)\n");
  return 0;
}
