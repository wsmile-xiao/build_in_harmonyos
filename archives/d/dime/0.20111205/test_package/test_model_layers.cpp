// Consumer use case for dime 0.20111205.
//
// Builds a model the way a CAD importer would — one layer in a LAYER
// table plus a 3DFACE mesh entity referencing that layer — writes it to
// DXF, reads it back, and verifies both the layer and the mesh survive
// the round trip.  Modeled on the upstream dxfsphere example.

#include <math.h>
#include <stdio.h>
#include <string.h>

#include <dime/Model.h>
#include <dime/Input.h>
#include <dime/Output.h>
#include <dime/sections/EntitiesSection.h>
#include <dime/sections/TablesSection.h>
#include <dime/tables/Table.h>
#include <dime/tables/LayerTable.h>
#include <dime/entities/3DFace.h>
#include <dime/util/Linear.h>

#define CHECK(cond, msg) \
  do { if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); return 1; } } while (0)

static int close_enough(float a, float b)
{
  return fabs(a - b) < 1e-4f;
}

int main(void)
{
  const char *layername = "MYLAYER1";
  dimeModel model;

  // ---- tables section with one LAYER table entry ----------------------
  dimeTablesSection *tables = new dimeTablesSection;
  CHECK(tables != NULL, "tables section allocated");
  model.insertSection(tables);

  dimeTable *layertable = new dimeTable(NULL);
  CHECK(layertable != NULL, "layer table allocated");
  layertable->setTableName("LAYER");

  dimeLayerTable *layer = new dimeLayerTable;
  CHECK(layer != NULL, "layer entry allocated");
  layer->setLayerName(layername, NULL);
  layer->setColorNumber(7);
  dimeParam param;
  param.string_data = "CONTINUOUS";
  layer->setRecord(6, param);
  param.int16_data = 64;
  layer->setRecord(70, param);
  layer->registerLayer(&model);
  layertable->insertTableEntry(layer);
  tables->insertTable(layertable);

  // ---- entities section with one 3DFACE triangle on that layer --------
  dimeEntitiesSection *entities = new dimeEntitiesSection;
  CHECK(entities != NULL, "entities section allocated");
  model.insertSection(entities);

  dime3DFace *face = new dime3DFace;
  CHECK(face != NULL, "3DFACE entity allocated");
  face->setLayer(model.getLayer(layername));
  dimeVec3f v0, v1, v2;
  v0.x = 0.0f;  v0.y = 0.0f;  v0.z = 0.0f;
  v1.x = 1.0f;  v1.y = 0.0f;  v1.z = 0.0f;
  v2.x = 0.5f;  v2.y = 1.0f;  v2.z = 0.25f;
  face->setTriangle(v0, v1, v2);

  char buf[64];
  const char *handle = model.getUniqueHandle(buf, sizeof(buf));
  CHECK(handle != NULL && handle[0] != '\0', "unique handle generated");
  param.string_data = handle;
  face->setRecord(5, param);
  model.addEntity(face);

  // ---- write it out ----------------------------------------------------
  // dimeOutput flushes and closes its FILE* only in the destructor, so
  // keep it in a scope of its own before dimeInput opens the file.
  {
    dimeOutput out;
    CHECK(out.setFilename("layers.dxf"), "output file opened");
    CHECK(model.write(&out), "model written to DXF");
  }

  // ---- read it back ----------------------------------------------------
  dimeInput in;
  CHECK(in.setFile("layers.dxf"), "input file opened");
  dimeModel model2;
  CHECK(model2.read(&in), "model read back from DXF");

  const dimeLayer *lay = model2.getLayer(layername);
  CHECK(lay != NULL, "layer survived round-trip");
  CHECK(lay->getLayerName() != NULL &&
        strcmp(lay->getLayerName(), layername) == 0,
        "layer name round-trip");
  CHECK(model2.getNumLayers() == 1, "exactly one layer");

  dimeSection *sec = model2.findSection("ENTITIES");
  CHECK(sec != NULL, "ENTITIES section found");
  dimeEntitiesSection *es = (dimeEntitiesSection *)sec;
  CHECK(es->getNumEntities() == 1, "exactly one entity");

  dimeEntity *ent = es->getEntity(0);
  CHECK(ent != NULL, "entity 0 present");
  CHECK(ent->isOfType(dimeBase::dime3DFaceType), "entity is a dime3DFace");

  dime3DFace *f2 = (dime3DFace *)ent;
  const dimeVec3f &r0 = f2->getVertex(0);
  const dimeVec3f &r1 = f2->getVertex(1);
  const dimeVec3f &r2 = f2->getVertex(2);
  CHECK(close_enough(r0.x, v0.x), "vertex0.x round-trip");
  CHECK(close_enough(r0.y, v0.y), "vertex0.y round-trip");
  CHECK(close_enough(r0.z, v0.z), "vertex0.z round-trip");
  CHECK(close_enough(r1.x, v1.x), "vertex1.x round-trip");
  CHECK(close_enough(r1.y, v1.y), "vertex1.y round-trip");
  CHECK(close_enough(r1.z, v1.z), "vertex1.z round-trip");
  CHECK(close_enough(r2.x, v2.x), "vertex2.x round-trip");
  CHECK(close_enough(r2.y, v2.y), "vertex2.y round-trip");
  CHECK(close_enough(r2.z, v2.z), "vertex2.z round-trip");

  printf("PASS: dime layer + 3DFACE round-trip (1 layer, 1 mesh entity, 9 coords verified)\n");
  return 0;
}
