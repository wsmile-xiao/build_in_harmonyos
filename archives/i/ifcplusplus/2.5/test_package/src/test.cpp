// test_package consumer test for ifcplusplus 2.5
//
// Verifies the public API of the installed package from a pure consumer
// point of view: load an IFC4 STEP model with ReaderSTEP, check that the
// model contains the expected entities, then serialize it back with
// WriterSTEP and verify the round-trip output.
#include <iostream>
#include <sstream>
#include <string>

#include <ifcpp/model/BuildingModel.h>
#include <ifcpp/IFC4X3/include/IfcProject.h>
#include <ifcpp/reader/ReaderSTEP.h>
#include <ifcpp/writer/WriterSTEP.h>

// Minimal but complete IFC4 STEP model (subset of the upstream
// examples/LoadFileExample/example.ifc data).
static const char* IFC4_SIMPLE_WALL =
    "ISO-10303-21;\n"
    "HEADER;\n"
    "FILE_DESCRIPTION(('IFC4'),'2;1');\n"
    "FILE_NAME('SimpleWall.ifc','2020-07-02T13:37:58',(''),('',''),'','IfcPlusPlus','');\n"
    "FILE_SCHEMA(('IFC4'));\n"
    "ENDSEC;\n"
    "DATA;\n"
    "#1= IFCWALL('0Av2L7p1f7EeLe2z5IPn4_',#97,'Hello Wall','Wall example',$,#93,#7,$,$);\n"
    "#7= IFCPRODUCTDEFINITIONSHAPE($,$,(#6,#36));\n"
    "#6= IFCSHAPEREPRESENTATION(#100,'Body','BRep',(#8));\n"
    "#8= IFCFACETEDBREP(#9);\n"
    "#9= IFCCLOSEDSHELL((#18,#21,#24,#27,#30,#33));\n"
    "#10= IFCCARTESIANPOINT((0.,0.,0.2));\n"
    "#11= IFCCARTESIANPOINT((5.,0.,0.2));\n"
    "#12= IFCCARTESIANPOINT((5.,0.25,0.2));\n"
    "#13= IFCCARTESIANPOINT((0.,0.25,0.2));\n"
    "#14= IFCCARTESIANPOINT((0.,0.,3.5));\n"
    "#15= IFCCARTESIANPOINT((5.,0.,3.5));\n"
    "#16= IFCCARTESIANPOINT((5.,0.25,3.5));\n"
    "#17= IFCCARTESIANPOINT((0.,0.25,3.5));\n"
    "#18= IFCFACE((#19));\n"
    "#19= IFCFACEOUTERBOUND(#20,.T.);\n"
    "#20= IFCPOLYLOOP((#10,#11,#12,#13));\n"
    "#21= IFCFACE((#22));\n"
    "#22= IFCFACEOUTERBOUND(#23,.T.);\n"
    "#23= IFCPOLYLOOP((#14,#15,#16,#17));\n"
    "#24= IFCFACE((#25));\n"
    "#25= IFCFACEOUTERBOUND(#26,.T.);\n"
    "#26= IFCPOLYLOOP((#10,#11,#15,#14));\n"
    "#27= IFCFACE((#28));\n"
    "#28= IFCFACEOUTERBOUND(#29,.T.);\n"
    "#29= IFCPOLYLOOP((#11,#12,#16,#15));\n"
    "#30= IFCFACE((#31));\n"
    "#31= IFCFACEOUTERBOUND(#32,.T.);\n"
    "#32= IFCPOLYLOOP((#12,#13,#17,#16));\n"
    "#33= IFCFACE((#34));\n"
    "#34= IFCFACEOUTERBOUND(#35,.T.);\n"
    "#35= IFCPOLYLOOP((#13,#10,#14,#17));\n"
    "#36= IFCSHAPEREPRESENTATION(#100,'Box','BoundingBox',(#37));\n"
    "#37= IFCBOUNDINGBOX(#38,5.,0.25,3.3);\n"
    "#38= IFCCARTESIANPOINT((0.,0.,0.2));\n"
    "#71= IFCPROJECT('0L5IS82L9848NinTRZ_5RM',#97,$,$,$,$,$,(#100),#99);\n"
    "#72= IFCSITE('2CicL0XFD27elhSbqOKpuk',#97,$,$,$,$,$,$,$,$,$,$,$,$);\n"
    "#73= IFCBUILDING('0qsZwQcGD8pPQ133wrGmO$',#97,$,$,$,#88,$,$,$,$,$,$);\n"
    "#74= IFCBUILDINGSTOREY('0Ehs$or6H5Che3YyhbG70I',#97,$,$,$,$,$,$,$,$);\n"
    "#75= IFCRELAGGREGATES('0JzZT74Y18Wecyg5muO63f',#97,$,$,#71,(#72));\n"
    "#76= IFCRELAGGREGATES('1BS024CHf9vRks0h5lSB1y',#97,$,$,#72,(#73));\n"
    "#77= IFCRELAGGREGATES('1BlQZKgQD0HuSifURRQL7f',#97,$,$,#73,(#74));\n"
    "#78= IFCRELCONTAINEDINSPATIALSTRUCTURE('2lsWhR_dPE5O3tzgQUpZCS',#97,$,$,(#1),#74);\n"
    "#79= IFCAXIS2PLACEMENT3D(#80,#81,#82);\n"
    "#80= IFCCARTESIANPOINT((0.,0.,0.));\n"
    "#81= IFCDIRECTION((0.,0.,1.));\n"
    "#82= IFCDIRECTION((1.,0.,0.));\n"
    "#83= IFCLOCALPLACEMENT($,#79);\n"
    "#88= IFCLOCALPLACEMENT(#83,#84);\n"
    "#84= IFCAXIS2PLACEMENT3D(#85,#86,#87);\n"
    "#85= IFCCARTESIANPOINT((2.7,0.,0.));\n"
    "#86= IFCDIRECTION((0.,0.,1.));\n"
    "#87= IFCDIRECTION((1.,0.,0.));\n"
    "#93= IFCLOCALPLACEMENT(#88,#89);\n"
    "#89= IFCAXIS2PLACEMENT3D(#90,#91,#92);\n"
    "#90= IFCCARTESIANPOINT((0.1,3.,0.));\n"
    "#91= IFCDIRECTION((0.,0.,1.));\n"
    "#92= IFCDIRECTION((1.,0.,0.));\n"
    "#94= IFCPERSON('MyID','MyFamilyName','MyGivenName',$,$,$,$,$);\n"
    "#95= IFCORGANIZATION('MyOrganization','My organizations name','My organizations description',$,$);\n"
    "#96= IFCPERSONANDORGANIZATION(#94,#95,$);\n"
    "#97= IFCOWNERHISTORY(#96,$,$,$,$,$,$,$);\n"
    "#98= IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);\n"
    "#99= IFCUNITASSIGNMENT((#98));\n"
    "#100= IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,0.00001,#79,$);\n"
    "ENDSEC;\n"
    "END-ISO-10303-21;\n";

int main()
{
    shared_ptr<BuildingModel> model = shared_ptr<BuildingModel>(new BuildingModel());
    ReaderSTEP reader;

    std::stringstream in(IFC4_SIMPLE_WALL);
    in.seekg(0, std::ios::end);
    std::streampos end_pos = in.tellg();
    in.seekg(0, std::ios::beg);

    reader.loadModelFromStream(in, end_pos, model);

    if (!model->getIfcProject())
    {
        std::cerr << "FAIL: no IfcProject in parsed model" << std::endl;
        return 1;
    }
    if (model->getMapIfcEntities().size() == 0)
    {
        std::cerr << "FAIL: model has zero entities" << std::endl;
        return 1;
    }
    std::cout << "parsed " << model->getMapIfcEntities().size() << " entities"
              << ", project classID: " << model->getIfcProject()->classID() << std::endl;

    WriterSTEP writer;
    std::stringstream out;
    writer.writeModelToStream(out, model);
    std::string written = out.str();
    if (written.find("IFCWALL") == std::string::npos)
    {
        std::cerr << "FAIL: written STEP output does not contain IFCWALL" << std::endl;
        return 1;
    }
    std::cout << "round-trip write OK, " << written.size() << " bytes" << std::endl;
    return 0;
}
