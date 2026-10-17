with Ada.Strings.Unbounded;
with Ada.Text_IO;
with CGI;

procedure Test_Adacgi is
   use Ada.Strings.Unbounded;
   use CGI;

   procedure Check (Condition : Boolean; Message : String) is
   begin
      if not Condition then
         Ada.Text_IO.Put_Line
           (File => Ada.Text_IO.Standard_Error,
            Item => "FAIL: " & Message);
         raise Program_Error;
      end if;
   end Check;

   First_Name  : constant String := Value (Key => "name", Index => 1);
   Second_Name : constant String := Value (Key => "name", Index => 2);
   Encoded     : constant String :=
     To_String (URL_Encode (To_Unbounded_String ("A B+C")));
   Decoded     : Unbounded_String := To_Unbounded_String ("A%20B%2BC");
begin
   URL_Decode (Decoded, Translate_Plus => False);

   Check (CGI_Method = Get, "REQUEST_METHOD was not parsed as GET");
   Check (Argument_Count = 2, "unexpected CGI argument count");
   Check (Key_Count ("name") = 2, "duplicate query key was not retained");
   Check (First_Name = "HarmonyOS", "first query value is incorrect");
   Check (Second_Name = "Ada CGI", "percent-decoded query value is incorrect");
   Check
     (Key_Value_Exists ("name", "Ada CGI"),
      "key/value lookup did not find the decoded value");
   Check
     (Encoded = "A%20B%2BC",
      "URL_Encode returned an unexpected value: " & Encoded);
   Check
     (To_String (Decoded) = "A B+C",
      "URL_Decode returned an unexpected value: " & To_String (Decoded));
   Check
     (HTML_Encode ("<tag>""&") = "&lt;tag&gt;&quot;&amp;",
      "HTML_Encode returned an unexpected value");
   Check (Line_Count ("") = 0, "empty value line count is incorrect");
   Check (Line_Count ("single line") = 1,
          "single-line value line count is incorrect");
   Check
     (Line_Count ("first" & ASCII.CR & ASCII.LF & "second") = 2,
      "line count after an embedded CRLF is incorrect");
   Check
     (Line_Count (ASCII.CR & ASCII.LF & "first") = 2,
      "line count with a leading CRLF is incorrect");

   Ada.Text_IO.Put_Line ("adacgi smoke: ok");
end Test_Adacgi;
