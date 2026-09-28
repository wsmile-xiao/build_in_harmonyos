with Ada.Text_IO;
with Ada.Directories;
with Ada.Strings.Unbounded;

with Alog.Logger;
with Alog.Facilities.File_Descriptor;

use Alog;

--  Alog consumer smoke test: attach an FD facility with a local log
--  file (relative path, so it works on read-only-/tmp systems), log
--  two messages through Logger, then read the file back and verify
--  both messages landed there.  Prints checks_passed=<n>; raises
--  Program_Error unless all three checks pass.
procedure Alog_Smoke is
   use Ada.Text_IO;
   use Ada.Strings.Unbounded;
   use type Ada.Directories.File_Size;

   Log_Name : constant String := "./alog_smoke.log";
   checks   : Natural := 0;

   Log : Logger.Instance (Init => True);

   function File_Contains (Path : String; Needle : String) return Boolean is
      Handle  : File_Type;
      Acc     : Unbounded_String;
      Content : String (1 .. 65536);
      Len     : Natural := 0;
   begin
      Open (Handle, In_File, Path);
      while not End_Of_File (Handle) loop
         declare
            Line : constant String := Get_Line (Handle);
         begin
            if Len + Line'Length + 1 <= Content'Last then
               Content (Len + 1 .. Len + Line'Length) := Line;
               Len := Len + Line'Length + 1;
               Content (Len) := ASCII.LF;
            end if;
         end;
      end loop;
      Close (Handle);
      if Len < Needle'Length then
         return False;
      end if;
      for I in 1 .. Len - Needle'Length + 1 loop
         if Content (I .. I + Needle'Length - 1) = Needle then
            return True;
         end if;
      end loop;
      return False;
   exception
      when others =>
         if Is_Open (Handle) then
            Close (Handle);
         end if;
         return False;
   end File_Contains;

begin
   Attach_FD_Facility :
   declare
      FD : constant Facilities.File_Descriptor.Handle :=
        new Facilities.File_Descriptor.Instance;
   begin
      FD.Set_Logfile (Path => Log_Name);
      Log.Attach_Facility (Facility => Facilities.Handle (FD));

      Log.Log_Message (Source => "Smoke",
                       Level  => Info,
                       Msg    => "Hello from Alog smoke");
      Log.Log_Message (Source => "Smoke",
                       Level  => Warning,
                       Msg    => "Second smoke message");
      Log.Clear;
   end Attach_FD_Facility;

   --  Check 1: the log file was created and is non-empty.
   if Ada.Directories.Exists (Log_Name)
     and then Ada.Directories.Size (Log_Name) > 0
   then
      checks := checks + 1;
   end if;

   --  Check 2: the first message is in the file.
   if File_Contains (Log_Name, "Hello from Alog smoke") then
      checks := checks + 1;
   end if;

   --  Check 3: the second message is in the file.
   if File_Contains (Log_Name, "Second smoke message") then
      checks := checks + 1;
   end if;

   Put_Line ("checks_passed=" & Natural'Image (checks));
   if checks < 3 then
      raise Program_Error;
   end if;
end Alog_Smoke;
