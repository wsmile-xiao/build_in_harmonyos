#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sbml/SBMLTypes.h>

static int test_core_model(void)
{
    SBMLDocument_t *doc = SBMLDocument_createWithLevelAndVersion(3, 2);
    Model_t *model;
    Compartment_t *comp;
    Species_t *species;

    if (doc == NULL) {
        printf("Test 1: FAIL (SBMLDocument_create returned NULL)\n");
        return 1;
    }
    if (SBMLDocument_getLevel(doc) != 3 || SBMLDocument_getVersion(doc) != 2) {
        printf("Test 1: FAIL (level/version mismatch)\n");
        SBMLDocument_free(doc);
        return 1;
    }
    model = SBMLDocument_createModel(doc);
    if (model == NULL || Model_setId(model, "test_model") != LIBSBML_OPERATION_SUCCESS) {
        printf("Test 1: FAIL (create model failed)\n");
        SBMLDocument_free(doc);
        return 1;
    }
    comp = Model_createCompartment(model);
    if (comp == NULL || Compartment_setId(comp, "cell") != LIBSBML_OPERATION_SUCCESS) {
        printf("Test 1: FAIL (create compartment failed)\n");
        SBMLDocument_free(doc);
        return 1;
    }
    Compartment_setSize(comp, 1.0);
    Compartment_setConstant(comp, 1);
    species = Model_createSpecies(model);
    if (species == NULL || Species_setId(species, "s1") != LIBSBML_OPERATION_SUCCESS) {
        printf("Test 1: FAIL (create species failed)\n");
        SBMLDocument_free(doc);
        return 1;
    }
    Species_setCompartment(species, "cell");
    Species_setInitialAmount(species, 5.0);
    Species_setBoundaryCondition(species, 0);
    if (Model_getNumCompartments(model) != 1 || Model_getNumSpecies(model) != 1) {
        printf("Test 1: FAIL (member counts wrong)\n");
        SBMLDocument_free(doc);
        return 1;
    }
    if (getLibSBMLVersion() <= 0) {
        printf("Test 1: FAIL (getLibSBMLVersion invalid)\n");
        SBMLDocument_free(doc);
        return 1;
    }
    printf("Test 1: OK (core model build, libsbml version %d)\n", getLibSBMLVersion());
    SBMLDocument_free(doc);
    return 0;
}

static int test_write_read_roundtrip(void)
{
    SBMLDocument_t *doc = SBMLDocument_createWithLevelAndVersion(3, 2);
    Model_t *model;
    char *xml = NULL;
    SBMLDocument_t *doc2 = NULL;
    int rc = 1;

    if (doc == NULL) {
        printf("Test 2: FAIL (create returned NULL)\n");
        return 1;
    }
    model = SBMLDocument_createModel(doc);
    if (model == NULL) {
        printf("Test 2: FAIL (create model failed)\n");
        SBMLDocument_free(doc);
        return 1;
    }
    Model_setId(model, "roundtrip");
    xml = writeSBMLToString(doc);
    if (xml == NULL || xml[0] == '\0') {
        printf("Test 2: FAIL (writeSBMLToString empty)\n");
        SBMLDocument_free(doc);
        return 1;
    }
    if (strstr(xml, "sbml") == NULL || strstr(xml, "roundtrip") == NULL) {
        printf("Test 2: FAIL (serialized SBML missing markers)\n");
        free(xml);
        SBMLDocument_free(doc);
        return 1;
    }
    doc2 = readSBMLFromString(xml);
    free(xml);
    if (doc2 == NULL) {
        printf("Test 2: FAIL (readSBMLFromString returned NULL)\n");
        SBMLDocument_free(doc);
        return 1;
    }
    if (SBMLDocument_getNumErrors(doc2) != 0) {
        printf("Test 2: FAIL (round-trip document has %d errors)\n", SBMLDocument_getNumErrors(doc2));
        SBMLDocument_free(doc);
        SBMLDocument_free(doc2);
        return 1;
    }
    if (SBMLDocument_getModel(doc2) == NULL) {
        printf("Test 2: FAIL (round-trip model missing)\n");
        SBMLDocument_free(doc);
        SBMLDocument_free(doc2);
        return 1;
    }
    printf("Test 2: OK (write/read round-trip, 0 errors)\n");
    SBMLDocument_free(doc);
    SBMLDocument_free(doc2);
    rc = 0;
    return rc;
}

int main(void)
{
    int passed = 0;
    const int discovered = 2;

    if (test_core_model() == 0) {
        passed++;
    }
    if (test_write_read_roundtrip() == 0) {
        passed++;
    }

    {
        int ok = (passed == discovered);
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"./test_libsbml\",\"discovered\":%d,\"passedCount\":%d}\n",
               ok ? "true" : "false", discovered, passed);
        printf("Consumer test: %d/%d passed\n", passed, discovered);
        return ok ? 0 : 1;
    }
}
