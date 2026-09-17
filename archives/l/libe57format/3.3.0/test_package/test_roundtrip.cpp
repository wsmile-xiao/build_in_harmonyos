// Consumer test 2/2: write a small E57 scan with the Simple API, read it
// back and verify the content. Mirrors upstream's CartesianPoints writer
// test and the SimpleReader read-back pattern (13 checks; any failure
// exits non-zero). The output file size is printed so the log proves the
// fixtures under test are real, non-empty files.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <iostream>
#include <sys/stat.h>

#include <E57Format/E57SimpleReader.h>
#include <E57Format/E57SimpleWriter.h>

namespace
{
int g_checks = 0;
int g_failed = 0;

void check( bool cond, const char *name )
{
   ++g_checks;
   if ( cond )
   {
      std::cout << "ok " << g_checks << ": " << name << "\n";
   }
   else
   {
      ++g_failed;
      std::cout << "FAIL " << g_checks << ": " << name << "\n";
   }
}

long fileSize( const char *path )
{
   struct stat st;
   if ( stat( path, &st ) != 0 )
   {
      return -1;
   }
   return static_cast<long>( st.st_size );
}
} // namespace

int main()
{
   const char *path = "./e57consumer.e57";
   std::remove( path );

   // 1. Write 8 cartesian float points (cube corners, like upstream's
   //    CartesianPoints test).
   try
   {
      e57::WriterOptions options;
      options.guid = "OHOS consumer smoke GUID";

      e57::Writer writer( path, options );
      check( writer.IsOpen(), "writer is open" );

      e57::Data3D header;
      header.guid = "OHOS consumer scan GUID";
      header.pointCount = 8;
      header.pointFields.cartesianXField = true;
      header.pointFields.cartesianYField = true;
      header.pointFields.cartesianZField = true;

      e57::Data3DPointsFloat points( header );
      for ( int64_t i = 0; i < 8; ++i )
      {
         const float v = static_cast<float>( i );
         points.cartesianX[i] = v;
         points.cartesianY[i] = v;
         points.cartesianZ[i] = v;
      }

      const int64_t index = writer.WriteData3DData( header, points );
      check( index == 0, "first scan index is 0" );
      check( writer.Close(), "writer closed" );
   }
   catch ( const e57::E57Exception &e )
   {
      std::cout << "FAIL: writer threw: " << e.errorStr() << "\n";
      return 1;
   }

   // 2. The file must exist and be non-empty.
   const long size = fileSize( path );
   std::cout << "info: wrote " << size << " bytes to " << path << "\n";
   check( size > 0, "output file is non-empty" );

   // 3. Read back and verify (upstream SimpleReader pattern).
   try
   {
      e57::Reader reader( path, {} );
      check( reader.IsOpen(), "reader is open" );
      check( reader.GetImage2DCount() == 0, "no image blocks" );
      check( reader.GetData3DCount() == 1, "one scan block" );

      e57::E57Root root;
      check( reader.GetE57Root( root ), "root header readable" );
      check( root.guid == "OHOS consumer smoke GUID", "file guid round-trips" );

      e57::Data3D header;
      check( reader.ReadData3D( 0, header ), "scan header readable" );
      check( header.pointCount == 8, "point count is 8" );

      e57::Data3DPointsFloat points( header );
      auto vectorReader =
         reader.SetUpData3DPointsData( 0, static_cast<size_t>( header.pointCount ), points );
      const unsigned got = vectorReader.read();
      vectorReader.close();
      check( got == 8, "read back 8 points" );

      bool valuesOk = true;
      for ( int64_t i = 0; i < 8; ++i )
      {
         const float v = static_cast<float>( i );
         if ( std::fabs( points.cartesianX[i] - v ) > 1e-5f ||
              std::fabs( points.cartesianY[i] - v ) > 1e-5f ||
              std::fabs( points.cartesianZ[i] - v ) > 1e-5f )
         {
            valuesOk = false;
            break;
         }
      }
      check( valuesOk, "point coordinates round-trip" );
   }
   catch ( const e57::E57Exception &e )
   {
      std::cout << "FAIL: reader threw: " << e.errorStr() << "\n";
      return 1;
   }

   std::cout << "RESULT: " << ( g_checks - g_failed ) << "/" << g_checks
             << " checks passed\n";
   return g_failed == 0 ? 0 : 1;
}
