--  libgmpada test_package consumer.
--  Exercises the Ada binding against the installed library with real
--  arithmetic assertions (not a link-only smoke test).
with Ada.Text_IO;
with GNU_Multiple_Precision;          use GNU_Multiple_Precision;
with GNU_Multiple_Precision.Big_Integers;
use GNU_Multiple_Precision.Big_Integers;

procedure Main is
   package IC is new Big_Integers.Integer_Conversions (Integer);
   use IC;

   Two      : constant Big_Integer := To_Big_Integer (2);
   Three    : constant Big_Integer := To_Big_Integer (3);
   Expected : constant Big_Integer :=
     Value ("1267650600228229401496703205376");
   R        : constant Big_Integer := Two ** 100;
begin
   if R /= Expected then
      Ada.Text_IO.Put_Line ("LIBA_GMPADA_CONSUMER_FAIL pow2_100");
      raise Program_Error;
   end if;

   if Image (-R) /= "-1267650600228229401496703205376" then
      Ada.Text_IO.Put_Line ("LIBA_GMPADA_CONSUMER_FAIL image");
      raise Program_Error;
   end if;

   if R / Three * Three + R rem Three /= R then
      Ada.Text_IO.Put_Line ("LIBA_GMPADA_CONSUMER_FAIL div_rem");
      raise Program_Error;
   end if;

   Ada.Text_IO.Put_Line ("LIBA_GMPADA_CONSUMER_OK");
end Main;
