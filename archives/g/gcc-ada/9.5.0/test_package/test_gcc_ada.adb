with Ada.Containers.Vectors;
with Ada.Strings.Fixed;
with Ada.Text_IO;

procedure Test_Gcc_Ada is
   Checks        : Natural := 0;
   Platform_Name : constant String := "HarmonyOS";

   procedure Check (Condition : Boolean; Name : String) is
   begin
      if not Condition then
         Ada.Text_IO.Put_Line ("FAILED: " & Name);
         raise Program_Error;
      end if;
      Checks := Checks + 1;
   end Check;

   protected Shared_Counter is
      procedure Increment;
      function Value return Natural;
   private
      Current : Natural := 0;
   end Shared_Counter;

   protected body Shared_Counter is
      procedure Increment is
      begin
         Current := Current + 1;
      end Increment;

      function Value return Natural is
      begin
         return Current;
      end Value;
   end Shared_Counter;

   task Worker is
      entry Run;
   end Worker;

   task body Worker is
   begin
      accept Run do
         Shared_Counter.Increment;
      end Run;
   end Worker;
begin
   Check (6 * 7 = 42, "integer arithmetic");
   Check (Platform_Name'Length = 9, "string attributes");
   Check
     (Ada.Strings.Fixed.Index (Platform_Name, "OS") = 8,
      "standard string runtime");

   declare
      package Integer_Vectors is new Ada.Containers.Vectors
        (Index_Type => Positive, Element_Type => Integer);
      Values : Integer_Vectors.Vector;
   begin
      Integer_Vectors.Append (Values, 21);
      Integer_Vectors.Append (Values, 21);
      Check
        (Integer_Vectors.Element (Values, 1)
         + Integer_Vectors.Element (Values, 2) = 42,
         "generic containers");
   end;

   declare
      Caught : Boolean := False;
   begin
      begin
         raise Constraint_Error;
      exception
         when Constraint_Error =>
            Caught := True;
      end;
      Check (Caught, "exception handling");
   end;

   Worker.Run;
   Check (Shared_Counter.Value = 1, "tasking runtime");

   if Checks /= 6 then
      raise Program_Error;
   end if;
   Ada.Text_IO.Put_Line ("gcc-ada checks passed:" & Natural'Image (Checks));
end Test_Gcc_Ada;
