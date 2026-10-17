#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <mujoco/mujoco.h>

/* Consumer test (R34): really exercises the public C API of the packaged
 * libmujoco.so — version query, MJCF model loading (parser + compiler path),
 * data allocation and an actual physics step with a behavioural assertion. */

static const char *kModelXml =
    "<mujoco model=\"conan-test\">\n"
    "  <option timestep=\"0.002\" gravity=\"0 0 -9.81\"/>\n"
    "  <worldbody>\n"
    "    <body name=\"ball\" pos=\"0 0 1\">\n"
    "      <freejoint/>\n"
    "      <geom type=\"sphere\" size=\"0.1\" mass=\"1\"/>\n"
    "    </body>\n"
    "  </worldbody>\n"
    "</mujoco>\n";

static int failures = 0;

static void check(const char *name, int cond) {
    if (cond) {
        printf("ok   %s\n", name);
    } else {
        fprintf(stderr, "FAIL %s\n", name);
        failures++;
    }
}

int main(void) {
    check("mj_versionString() non-empty", mj_versionString() != NULL &&
                                          strlen(mj_versionString()) > 0);
    check("mj_version() == 222 for 2.2.2", mj_version() == 222);

    /* write the minimal MJCF model next to the executable (cwd is writable) */
    const char *path = "conan_test_model.xml";
    FILE *f = fopen(path, "w");
    if (!f) {
        fprintf(stderr, "FAIL cannot write %s\n", path);
        return 1;
    }
    fputs(kModelXml, f);
    fclose(f);

    char err[512] = {0};
    mjModel *m = mj_loadXML(path, NULL, err, sizeof(err));
    check("mj_loadXML() loads MJCF model", m != NULL);
    if (!m) {
        fprintf(stderr, "mj_loadXML error: %s\n", err);
        return 1;
    }
    check("model has nq == 7 (freejoint)", m->nq == 7);

    mjData *d = mj_makeData(m);
    check("mj_makeData() allocates mjData", d != NULL);
    if (!d) return 1;

    mjtNum t0 = d->time;
    mj_forward(m, d);
    for (int i = 0; i < 50; i++) {
        mj_step(m, d);
    }
    check("mj_step() advances simulation time", d->time > t0);
    /* free-falling ball: z position must drop below its 1.0 start */
    check("gravity moves the free joint (qpos[2] < 1.0)", d->qpos[2] < 1.0);
    check("no NaN after 50 steps", d->qpos[2] == d->qpos[2]);

    mj_deleteData(d);
    mj_deleteModel(m);
    remove(path);

    if (failures != 0) {
        fprintf(stderr, "test_mujoco: %d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("test_mujoco: 8/8 API assertions passed (mujoco %s)\n",
           mj_versionString());
    return 0;
}
