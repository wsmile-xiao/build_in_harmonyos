------------------------------------------------------------------------------
--  Florist consumer check (libflorist / POSIX.5 Ada bindings)
--
--  This program REALLY links against libflorist and CALLS its API -- it is not
--  a print-only shell.  Every check below goes through a Florist subprogram,
--  so the CI L1e destructive reverse-check (product directory moved away ->
--  link/run must fail) holds: the linker must resolve the Florist symbols and
--  the executable must load the Ada runtime they depend on.
--
--  Verified API surface (from libsrc/ of the packaged source):
--    POSIX.Process_Identification.Get_Process_ID      -> Process_ID
--    POSIX.Process_Identification.Image (ID)          -> Standard.String
--    POSIX.Process_Environment.Is_Environment_Variable(POSIX_String) -> Boolean
--    POSIX.Process_Environment.Environment_Value_Of   -> POSIX_String
--    POSIX.To_POSIX_String / POSIX.To_String          (type conversions)
--    POSIX.Files.Is_Directory (Pathname)              -> Boolean
--
--  NOTE: string literals are converted through typed constants on purpose --
--  POSIX.To_POSIX_String is overloaded on String and Wide_String, so passing
--  an untyped literal is ambiguous (compile error).
------------------------------------------------------------------------------
with Ada.Text_IO;

with POSIX;
with POSIX.Process_Identification;
with POSIX.Process_Environment;
with POSIX.Files;

procedure Florist_Consumer is

   Failures : Natural := 0;

   procedure Check (Condition : Boolean; What : String) is
   begin
      if Condition then
         Ada.Text_IO.Put_Line ("  ok   : " & What);
      else
         Failures := Failures + 1;
         Ada.Text_IO.Put_Line ("  FAIL : " & What);
      end if;
   end Check;

   Path_Text : constant String := "PATH";
   Path_Name : constant POSIX.POSIX_String :=
     POSIX.To_POSIX_String (Path_Text);

   Root_Text : constant String := "/";
   Root_Name : constant POSIX.POSIX_String :=
     POSIX.To_POSIX_String (Root_Text);

   Absent_Text : constant String := "/this/path/should/not/exist";
   Absent_Name : constant POSIX.POSIX_String :=
     POSIX.To_POSIX_String (Absent_Text);

   Pid_Image : constant String :=
     POSIX.Process_Identification.Image
       (POSIX.Process_Identification.Get_Process_ID);

   Path_Value : constant POSIX.POSIX_String :=
     POSIX.Process_Environment.Environment_Value_Of (Path_Name);

begin
   Ada.Text_IO.Put_Line ("libflorist consumer: POSIX.5 Ada bindings");

   --  1. Call a Florist function whose result is derived from getpid(2).
   Check (Pid_Image'Length > 0, "Get_Process_ID/Image returned a value");

   --  2. Query the process environment through the Florist binding.
   Check (POSIX.Process_Environment.Is_Environment_Variable (Path_Name),
          "Is_Environment_Variable(""PATH"") is True");

   Check (POSIX.To_String (Path_Value)'Length > 0,
          "Environment_Value_Of(""PATH"") is non-empty");

   --  3. Exercise the file-status binding against a path that must exist.
   Check (POSIX.Files.Is_Directory (Root_Name),
          "Is_Directory(""/"") is True");

   Check (not POSIX.Files.Is_Directory (Absent_Name),
          "Is_Directory(absent path) is False");

   if Failures = 0 then
      Ada.Text_IO.Put_Line ("FLORIST_CONSUMER_OK");
   else
      Ada.Text_IO.Put_Line ("FLORIST_CONSUMER_FAILED");
      raise Program_Error with "consumer checks failed";
   end if;
end Florist_Consumer;
