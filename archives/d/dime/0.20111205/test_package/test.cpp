// Consumer smoke test for dime 0.20111205.
//
// Builds a DXF model in memory (one LINE entity), writes it out with
// dimeOutput, reads it back with dimeInput, and verifies the entity and
// its coordinates survive the round trip.

#include <math.h>
#include <stdio.h>

#include <dime/Model.h>
#include <dime/Input.h>
#include <dime/Output.h>
#include <dime/sections/EntitiesSection.h>
#include <dime/entities/Line.h>
#include <dime/util/Linear.h>

#define CHECK(cond, msg) \
  do { if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); return 1; } } while (0)

static int close_enough(float a, float b)
{
  return fabs(a - b) < 1e-4f;
}

int main(void)
{
  // ---- build a minimal model with one LINE entity ----------------------
  dimeModel model;
  dimeEntitiesSection *entities = new dimeEntitiesSection;
  CHECK(entities != NULL, "entities section allocated");
  model.insertSection(entities);

  dimeLine *line = new dimeLine;
  CHECK(line != NULL, "line entity allocated");
  dimeVec3f v0, v1;
  v0.x = 1.5f;   v0.y = -2.25f; v0.z = 3.75f;
  v1.x = -4.5f;  v1.y = 5.25f;  v1.z = -6.125f;
  line->setCoords(0, v0);
  line->setCoords(1, v1);

  // unique handle, as needed for AutoCAD-compatible files
  char buf[64];
  const char *handle = model.getUniqueHandle(buf, sizeof(buf));
  CHECK(handle != NULL && handle[0] != '\0', "unique handle generated");
  dimeParam param;
  param.string_data = handle;
  line->setRecord(5, param);

  model.addEntity(line);

  // ---- write it out ----------------------------------------------------
  // dimeOutput flushes and closes its FILE* only in the destructor, so
  // keep it in a scope of its own: the file must be complete on disk
  // before dimeInput opens it (setFilePointer treats filesize==0 as
  // failure).
  {
    dimeOutput out;
    CHECK(out.setFilename("smoke.dxf"), "output file opened");
    CHECK(model.write(&out), "model written to DXF");
  }

  // ---- read it back ----------------------------------------------------
  dimeInput in;
  CHECK(in.setFile("smoke.dxf"), "input file opened");
  dimeModel model2;
  CHECK(model2.read(&in), "model read back from DXF");

  dimeSection *sec = model2.findSection("ENTITIES");
  CHECK(sec != NULL, "ENTITIES section found");
  dimeEntitiesSection *es = (dimeEntitiesSection *)sec;
  CHECK(es->getNumEntities() == 1, "exactly one entity after round-trip");

  dimeEntity *ent = es->getEntity(0);
  CHECK(ent != NULL, "entity 0 present");
  CHECK(ent->isOfType(dimeBase::dimeLineType), "entity is a dimeLine");

  dimeLine *l2 = (dimeLine *)ent;
  const dimeVec3f &r0 = l2->getCoords(0);
  const dimeVec3f &r1 = l2->getCoords(1);
  CHECK(close_enough(r0.x, v0.x), "vertex0.x round-trip");
  CHECK(close_enough(r0.y, v0.y), "vertex0.y round-trip");
  CHECK(close_enough(r0.z, v0.z), "vertex0.z round-trip");
  CHECK(close_enough(r1.x, v1.x), "vertex1.x round-trip");
  CHECK(close_enough(r1.y, v1.y), "vertex1.y round-trip");
  CHECK(close_enough(r1.z, v1.z), "vertex1.z round-trip");

  printf("PASS: dime write/read round-trip (1 LINE entity, 6 coords verified)\n");
  return 0;
}
