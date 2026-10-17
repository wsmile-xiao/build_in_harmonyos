/* GL entry-point stubs for linking glu_glew_shim_selftest() into the
 * consumer-side test binary (test_package).
 *
 * The shim object (packaged libGLU.a) references two GL entry points:
 *   - glTexImage2D  (gluBuild2DMipmaps texture path)
 *   - glMultMatrixd (gluPerspective path)
 * The self-test only exercises pure matrix maths - these stubs are never
 * called at runtime; they merely satisfy the static linker. Same approach
 * as the build() probe in the main recipe (gl_stub_for_probe.cpp): linking
 * the real gl4es libGL would crash during its loader init on headless
 * workers (no LIBGL_* environment).
 */
void glTexImage2D(void) {}
void glMultMatrixd(const double *unused) { (void)unused; }
