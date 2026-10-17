-- Non-interactive smoke consumer for the AdaCurses (libncursesada) binding.
-- It links against the installed Ada library and exercises a minimal screen
-- lifecycle.  The final marker goes to stdout so the pty driver can assert it.
with Ada.Text_IO;
with Terminal_Interface.Curses; use Terminal_Interface.Curses;

procedure Main is
   Win : Window;
begin
   Init_Screen;
   Win := Standard_Window;
   Add (Win, 2, 0, "libncursesada binding works");
   Refresh (Win);
   End_Windows;
   Ada.Text_IO.Put_Line ("LIBNCURSESADA_CONSUMER_OK");
end Main;
