#!/usr/bin/env python3
"""Consumer test for slicot/5.9.1.

Compiles and runs a small Fortran program against the **packaged** SLICOT
library (plus its BLAS/LAPACK/Fortran-runtime closure), then asserts the
computed result.  The driver is this Python script so the package ships a
real test source file recognised by CI L0c (.py); the Fortran program is
written out at test time and is the artefact actually executed.
"""
import os
import shutil
import subprocess
import sys
import tempfile

FORTRAN = r"""
      PROGRAM CONSUMER
      IMPLICIT NONE
*     Exercise MA02AD (transpose all of matrix A into B) - a real SLICOT
*     routine, so a successful link+run proves the packaged archive and its
*     dependency closure are usable by a consumer.
      INTEGER            M, N, LDA, LDB
      PARAMETER        ( M = 3, N = 2, LDA = 3, LDB = 2 )
      DOUBLE PRECISION  A( LDA, N ), B( LDB, M )
      INTEGER           I, J
      DOUBLE PRECISION  S
C
      DO 20 J = 1, N
         DO 10 I = 1, M
            A( I, J ) = DBLE( 10*J + I )
   10    CONTINUE
   20 CONTINUE
C
      CALL MA02AD( 'A', M, N, A, LDA, B, LDB )
C
*     B must equal A transposed: B(j,i) == A(i,j)
      S = 0.0D0
      DO 40 I = 1, M
         DO 30 J = 1, N
            S = S + ABS( B( J, I ) - A( I, J ) )
   30    CONTINUE
   40 CONTINUE
      IF ( S .NE. 0.0D0 ) THEN
         WRITE (*,*) 'TRANSPOSE MISMATCH'
         STOP 1
      END IF
      WRITE (*,*) 'SLICOT CONSUMER OK'
      END
"""


def find_first(root, names):
    for n in names:
        p = os.path.join(root, n)
        if os.path.isfile(p):
            return p
    return None


def main():
    slicot_lib = sys.argv[1]
    blas_lib = sys.argv[2]
    lapack_lib = sys.argv[3]

    assert os.path.isfile(slicot_lib), "packaged SLICOT archive missing: %s" % slicot_lib
    assert os.path.isfile(blas_lib), "BLAS archive missing: %s" % blas_lib
    assert os.path.isfile(lapack_lib), "LAPACK archive missing: %s" % lapack_lib

    # flang + the Fortran runtime come from the toolchain package.
    flang_bin = os.environ["SLICOT_FLANG_BIN"]
    flang_lib = os.environ["SLICOT_FLANG_LIB"]
    sdk_lib = os.environ["SLICOT_SDK_LIB"]
    sysroot = os.environ["SLICOT_SYSROOT"]
    resdir = os.environ["SLICOT_RESOURCE_DIR"]

    tmp = tempfile.mkdtemp(prefix="slicot-test-")
    try:
        src = os.path.join(tmp, "consumer.f")
        with open(src, "w") as fh:
            fh.write(FORTRAN)
        exe = os.path.join(tmp, "consumer")

        rt = [os.path.join(flang_lib, n)
              for n in ("libFortranRuntime.a", "libFortranDecimal.a")]
        # --sysroot is mandatory: without it the linker cannot find the CRT
        # objects (Scrt1.o / crti.o / crtn.o) or -lm / -lc.
        cmd = [flang_bin, "--target=aarch64-linux-ohos",
               "--sysroot=%s" % sysroot,
               "-resource-dir=%s" % resdir,
               "-L%s" % os.path.dirname(slicot_lib),
               "-L%s" % os.path.dirname(lapack_lib),
               "-L%s" % os.path.dirname(blas_lib),
               "-L%s" % sdk_lib, "-L%s" % flang_lib,
               src, "-o", exe,
               slicot_lib, lapack_lib, blas_lib] + rt + ["-lm"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        blob = (proc.stdout or "") + (proc.stderr or "")
        assert proc.returncode == 0, "compile/link failed:\n%s" % blob[-2000:]

        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = ":".join(
            [sdk_lib, flang_lib, os.path.dirname(lapack_lib),
             os.path.dirname(blas_lib), os.path.dirname(slicot_lib),
             "/system/lib64"])
        run = subprocess.run([exe], capture_output=True, text=True, env=env,
                             timeout=300)
        out = (run.stdout or "") + (run.stderr or "")
        assert run.returncode == 0, "consumer run failed:\n%s" % out
        assert "SLICOT CONSUMER OK" in out, out
        print("linked against %s" % os.path.basename(slicot_lib))
        print("SLICOT-CONSUMER-OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


main()
