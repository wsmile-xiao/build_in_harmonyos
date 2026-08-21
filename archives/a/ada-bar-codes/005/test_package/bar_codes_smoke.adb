with Ada.Text_IO;
with Bar_Codes;
with Bar_Codes_Media;

procedure Bar_Codes_Smoke is
   use Ada.Text_IO;

   checks : Natural := 0;

   fit : Bar_Codes.Module_Box;
   --  String 是非限定数组子类型，未初始化声明在 Ada 中非法
   --  （"unconstrained subtype not allowed"）；直接以函数返回值
   --  初始化，长度即真实 SVG 输出长度。
   svg : String := Bar_Codes_Media.SVG_Bar_Code
     (Bar_Codes.Code_QR_Low, 100.0, 100.0, "mm", "Hello");
begin
   -- 1D: Code 128 编码 "Hello" 的模块尺寸必须非空
   fit := Bar_Codes.Fitting (Bar_Codes.Code_128, "Hello");
   if fit.width > 0 and fit.height > 0 then
      checks := checks + 1;
   end if;

   -- 2D: QR 码的模块尺寸必须非空
   fit := Bar_Codes.Fitting (Bar_Codes.Code_QR_Low, "Hello");
   if fit.width > 0 and fit.height > 0 then
      checks := checks + 1;
   end if;

   -- SVG 矢量输出必须非空
   svg := Bar_Codes_Media.SVG_Bar_Code
     (Bar_Codes.Code_QR_Low, 100.0, 100.0, "mm", "Hello");
   if svg'Length > 0 then
      checks := checks + 1;
   end if;

   Put_Line ("checks_passed=" & Natural'Image (checks));
   if checks < 3 then
      raise Program_Error;
   end if;
end Bar_Codes_Smoke;
