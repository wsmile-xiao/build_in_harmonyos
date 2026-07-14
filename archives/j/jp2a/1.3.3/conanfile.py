#!/usr/bin/env python3
"""Conan recipe for jp2a 1.3.3."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Jp2aConan(ConanFile):
    name = "jp2a"
    version = "1.3.3"
    description = "Convert JPEG and WebP images to ASCII"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Talinx/jp2a"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libwebp/1.6.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as exc:
            self.output.warning(f"upstream download failed, retrying through mirror: {exc}")
            sources = dict(self.conan_data["sources"])
            sources["url"] = "https://ghproxy.net/" + sources["url"]
            get(self, **sources, strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-silent-rules")
        tc.configure_args.append("--disable-curl")
        tc.configure_args.append("--disable-termlib")
        tc.configure_args.append("--disable-doxygen-doc")
        tc.configure_args.append("--disable-doxygen-html")
        tc.extra_cflags.append(f"-I{self.source_folder}/include")
        tc.extra_cflags.append(f"-I{self.source_folder}/src")
        for dep in self.dependencies.values():
            for include_dir in dep.cpp_info.includedirs:
                tc.extra_cflags.append(f"-I{include_dir}")
            for lib_dir in dep.cpp_info.libdirs:
                tc.extra_ldflags.append(f"-L{lib_dir}")
        tc.generate()

    def build(self):
        image_h = os.path.join(self.source_folder, "include", "image.h")
        image_c = os.path.join(self.source_folder, "src", "image.c")
        replace_in_file(self, image_h, "#include \"png.h\"\n", "typedef void *png_structp;\ntypedef void *png_infop;\ntypedef unsigned char *png_bytep;\n")
        replace_in_file(self, image_c, "#include \"png.h\"\n", "")
        replace_in_file(self, image_c, "#include <libexif/exif-data.h>\n#include <libexif/exif-loader.h>\n", "")
        replace_in_file(
            self,
            image_c,
            '''void print_info_png(const png_structp png_ptr, const png_infop info_ptr) {
\tfprintf(stderr, "Source width: %d\\n", png_get_image_width(png_ptr, info_ptr));
\tfprintf(stderr, "Source height: %d\\n", png_get_image_height(png_ptr, info_ptr));
\tfprintf(stderr, "Source channel count: %d ", png_get_channels(png_ptr, info_ptr));
\tswitch ( png_get_color_type(png_ptr, info_ptr) ) {
\t\tcase PNG_COLOR_TYPE_GRAY:
\t\t\tfprintf(stderr, "(G)\\n");
\t\t\tbreak;
\t\tcase PNG_COLOR_TYPE_GRAY_ALPHA:
\t\t\tfprintf(stderr, "(GA)\\n");
\t\t\tbreak;
\t\tcase PNG_COLOR_TYPE_PALETTE:
\t\t\tfprintf(stderr, "(Palette)\\n");
\t\t\tbreak;
\t\tcase PNG_COLOR_TYPE_RGB:
\t\t\tfprintf(stderr, "(RGB)\\n");
\t\t\tbreak;
\t\tcase PNG_COLOR_TYPE_RGB_ALPHA:
\t\t\tfprintf(stderr, "(RGBA)\\n");
\t\t\tbreak;
\t}
\tswitch ( png_get_interlace_type(png_ptr, info_ptr) ) {
\t\tcase PNG_INTERLACE_NONE:
\t\t\tfprintf(stderr, "Source interlacing: None\\n");
\t\t\tbreak;
\t\tcase PNG_INTERLACE_ADAM7:
\t\t\tfprintf(stderr, "Source interlacing: Adam7\\n");
\t\t\tbreak;
\t}
\tfprintf(stderr, "Source bit depth: %d\\n", png_get_bit_depth(png_ptr, info_ptr));
\tfprintf(stderr, "Output width: %d\\n", width);
\tfprintf(stderr, "Output height: %d\\n", height);
\tfprintf(stderr, "Output palette (%d chars): '%s'\\n", ascii_palette_length, ascii_palette);
}
''',
            '''void print_info_png(const png_structp png_ptr, const png_infop info_ptr) {
\t(void) png_ptr;
\t(void) info_ptr;
}
''',
        )
        replace_in_file(
            self,
            image_c,
            '''void process_scanline_png(const png_bytep row, const int current_y, const int color_components, Image* i) {
\tstatic int lasty = 0;
\tconst int y = ROUND( i->resize_y * (float) current_y );

\t// include all scanlines since last call

\tfloat *pixel, *red, *green, *blue, *alpha;

\tpixel  = &i->pixel[lasty * i->src_width];
\tred = green = blue = NULL;
\talpha = &i->alpha[lasty * i->src_width];

\tif ( usecolors ) {
\t\tint offset = lasty * i->src_width;
\t\tred   = &i->red  [offset];
\t\tgreen = &i->green[offset];
\t\tblue  = &i->blue [offset];
\t}

\twhile ( lasty <= y ) {

\t\tint x;
\t\tfor ( x=0; x < i->src_width; ++x ) {

\t\t\tint adds = 0;

\t\t\tfloat v, r, g, b, a;
\t\t\tv = r = g = b = a = 0.0f;

\t\t\tfor ( int j = i->lookup_resx[x] ; j < i->lookup_resx[x+1]; ++j ) {
\t\t\t\tpng_byte* src_pixel = &(row[j * color_components]);

\t\t\t\tif ( color_components < 3 ) {
\t\t\t\t\tv += GRAY[src_pixel[0]];
\t\t\t\t\tif ( color_components == 2 )
\t\t\t\t\t\ta += ALPHA[src_pixel[1]];
\t\t\t\t} else {
\t\t\t\t\tv += RED[src_pixel[0]] + GREEN[src_pixel[1]] + BLUE[src_pixel[2]];

\t\t\t\t\tif ( usecolors ) {
\t\t\t\t\t\tr += (float) src_pixel[0]/255.0f;
\t\t\t\t\t\tg += (float) src_pixel[1]/255.0f;
\t\t\t\t\t\tb += (float) src_pixel[2]/255.0f;
\t\t\t\t\t}
\t\t\t\t\tif ( color_components == 4 )
\t\t\t\t\t\ta += ALPHA[src_pixel[3]];
\t\t\t\t}

\t\t\t\t++adds;
\t\t\t}

\t\t\tpixel[x] += adds>1 ? v / (float) adds : v;

\t\t\tif ( usecolors ) {
\t\t\t\tred  [x] += adds>1 ? r / (float) adds : r;
\t\t\t\tgreen[x] += adds>1 ? g / (float) adds : g;
\t\t\t\tblue [x] += adds>1 ? b / (float) adds : b;
\t\t\t}
\t\t\tif ( color_components == 1 || color_components == 3 ) {
\t\t\t\talpha[x] = 1.0;
\t\t\t} else {
\t\t\t\tif ( a == 0.0 )
\t\t\t\t\talpha[x] = 0.0;
\t\t\t\telse
\t\t\t\t\talpha[x] = adds>1 ? a / (float) adds : a;
\t\t\t}
\t\t}

\t\t++i->yadds[lasty++];

\t\tpixel += i->src_width;
\t\talpha += i->src_width;

\t\tif ( usecolors ) {
\t\t\tred   += i->src_width;
\t\t\tgreen += i->src_width;
\t\t\tblue  += i->src_width;
\t\t}
\t}

\tlasty = y;
}
''',
            '''void process_scanline_png(const png_bytep row, const int current_y, const int color_components, Image* i) {
\t(void) row;
\t(void) current_y;
\t(void) color_components;
\t(void) i;
}
''',
        )
        replace_in_file(
            self,
            image_c,
            '''Orientation get_orientation(FILE *imageFP) {
\tchar orientationTag[13] = "Top-left";  // default to horizontal/normal

\tsize_t size;
\tunsigned char data[1024];
\tExifData *edata;
\tExifLoader *loader;
\tloader = exif_loader_new();
\twhile ( 1 ) {
\t\tsize = fread(data, 1, sizeof(data), imageFP);
\t\tif (size <= 0) {
\t\t\tbreak;
\t\t}
\t\tif (!exif_loader_write(loader, data, size)) {
\t\t\tbreak;
\t\t}
\t}
\trewind(imageFP);
\tedata = exif_loader_get_data(loader);
\texif_loader_unref(loader);
\tif ( edata ) {
\t\tExifEntry *entry = exif_content_get_entry(edata->ifd[EXIF_IFD_0], EXIF_TAG_ORIENTATION);
\t\tif ( entry ) {
\t\t\texif_entry_get_value(entry, orientationTag, sizeof(orientationTag));
\t\t}
\t\texif_data_unref(edata);
\t}

\tif ( strcmp(orientationTag, "Top-left" ) == 0) {
\t\treturn HORIZONTAL;
\t} else if ( strcmp(orientationTag, "Top-right" ) == 0) {
\t\treturn MIRROR_HORIZONTAL;
\t} else if ( strcmp(orientationTag, "Bottom-right" ) == 0) {
\t\treturn ROTATE_180;
\t} else if ( strcmp(orientationTag, "Bottom-left" ) == 0) {
\t\treturn MIRROR_VERTICAL;
\t} else if ( strcmp(orientationTag, "Left-top" ) == 0) {
\t\treturn MIRROR_HORIZONTAL_ROTATE_90;
\t} else if ( strcmp(orientationTag, "Right-top" ) == 0) {
\t\treturn ROTATE_270;
\t} else if ( strcmp(orientationTag, "Right-bottom" ) == 0) {
\t\treturn MIRROR_HORIZONTAL_ROTATE_270;
\t} else if ( strcmp(orientationTag, "Left-bottom" ) == 0) {
\t\treturn ROTATE_90;
\t}
\treturn HORIZONTAL;
}
''',
            '''Orientation get_orientation(FILE *imageFP) {
\trewind(imageFP);
\treturn HORIZONTAL;
}
''',
        )
        replace_in_file(
            self,
            image_c,
            '''void decompress_png(FILE *fp, FILE *fout, error_collector *errors) {
\tif ( errors->png_status ) {
\t\tprint_errors(errors);
\t\treturn;
\t}
\tImage image;
\tint number_bytes_to_check = 8;
\tchar header[number_bytes_to_check];
\tif ( fread(&header, 1, number_bytes_to_check, fp) != number_bytes_to_check || png_sig_cmp(header, 0, number_bytes_to_check) ) {
\t\terrors->png_error_msg = "Not a PNG file: Wrong signature";
\t\terrors->png_status = 1;
\t\trewind(fp);
\t\tdecompress_jpeg(fp, fout, errors);
\t\treturn;
\t}
\tpng_structp png_ptr = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
\tif ( !png_ptr ) {
\t\tfprintf(stderr, "Unable to setup PNG reading, skipping file.\\n");
\t\treturn;
\t}
\tpng_infop info_ptr = png_create_info_struct(png_ptr);
\tif ( !info_ptr ) {
\t\tfprintf(stderr, "Unable to setup PNG reading, skipping file.\\n");
\t\tpng_destroy_read_struct(&png_ptr, NULL, NULL);
\t\treturn;
\t}
\tif ( setjmp(png_jmpbuf(png_ptr)) ) {
\t\terrors->png_error_msg = "Not a valid PNG file.";
\t\terrors->png_status = 1;
\t\tpng_destroy_read_struct(&png_ptr, &info_ptr, NULL);
\t\trewind(fp);
\t\tdecompress_webp(fp, fout, errors);
\t\treturn;
\t}
\tpng_init_io(png_ptr, fp);
\tpng_set_sig_bytes(png_ptr, number_bytes_to_check);
\tpng_read_info(png_ptr, info_ptr);

\tint png_width = png_get_image_width(png_ptr, info_ptr);
\tint png_height = png_get_image_height(png_ptr, info_ptr);

\taspect_ratio(png_width, png_height, 0);

\tif ( verbose ) print_info_png(png_ptr, info_ptr);

\tif ( height != 0 && width != 0 ) {
\t\tmalloc_image(&image, 0);
\t\tclear(&image);


\t\t// peform transformations (after printing the info):
\t\tif ( png_get_color_type(png_ptr, info_ptr) == PNG_COLOR_TYPE_PALETTE )
\t\t\tpng_set_palette_to_rgb(png_ptr);
\t\tif ( png_get_bit_depth(png_ptr, info_ptr) < 8 ) {
\t\t\tif ( png_get_channels(png_ptr, info_ptr) < 3 ) {
\t\t\t\tpng_set_expand_gray_1_2_4_to_8(png_ptr);
\t\t\t} else {
\t\t\t\tpng_set_expand(png_ptr);
\t\t\t}
\t\t}
\t\tif ( png_get_valid(png_ptr, info_ptr, PNG_INFO_tRNS) )
\t\t\tpng_set_tRNS_to_alpha(png_ptr);
\t\tif ( png_get_bit_depth(png_ptr, info_ptr) == 16 )
\t\t\tpng_set_strip_16(png_ptr);
\t\tint number_of_passes = png_set_interlace_handling(png_ptr);
\t\tpng_read_update_info(png_ptr, info_ptr);

\t\tinit_image(&image, png_width, png_height);

\t\tif ( verbose )
\t\t\tprint_progress(0.0);
\t\tif ( png_get_interlace_type(png_ptr, info_ptr) == PNG_INTERLACE_NONE ) {
\t\t\tpng_bytep row_pointer = png_malloc(png_ptr, png_width * png_get_channels(png_ptr, info_ptr) * 1);
\t\t\tfor ( int y = 0; y < png_height; y++ ) {
\t\t\t\tpng_read_row(png_ptr, row_pointer, NULL);
\t\t\t\tprocess_scanline_png(row_pointer, y, png_get_channels(png_ptr, info_ptr), &image);
\t\t\t\tif ( verbose )
\t\t\t\t\tprint_progress((float) y/png_height);
\t\t\t}
\t\t\tpng_free(png_ptr, row_pointer);
\t\t} else {
\t\t\tpng_bytepp row_pointers = png_malloc(png_ptr, png_height * sizeof(png_bytep));
\t\t\tfor ( int i = 0; i < png_height; ++i )
\t\t\t\trow_pointers[i] = NULL;
\t\t\tfor ( int i = 0; i < png_height; ++i )
\t\t\t\trow_pointers[i] = png_malloc(png_ptr, png_width * png_get_channels(png_ptr, info_ptr) * 1);
\t\t\t// png_read_image would do the same thing, but progress could not be displayed
\t\t\tfor ( int passes = 0; passes < number_of_passes; ++passes ) {
\t\t\t\tpng_read_rows(png_ptr, row_pointers, NULL, png_height);
\t\t\t\tif ( verbose )
\t\t\t\t\tprint_progress((float) (passes + 1)/number_of_passes);
\t\t\t}
\t\t\tfor ( int y = 0; y < png_height; y++ ) {
\t\t\t\tprocess_scanline_png(row_pointers[y], y, png_get_channels(png_ptr, info_ptr), &image);
\t\t\t}
\t\t\tfor ( int i = 0; i < png_height; ++i )
\t\t\t\tpng_free(png_ptr, row_pointers[i]);
\t\t\tpng_free(png_ptr, row_pointers);
\t\t}
\t\tif ( verbose )
\t\t\tprint_progress(1.0);
\t\tpng_read_end(png_ptr, NULL);

\t\tprint_image(&image, fout);

\t\tfree_image(&image);
\t}

\tpng_destroy_read_struct(&png_ptr, &info_ptr, NULL);
}
''',
            '''void decompress_png(FILE *fp, FILE *fout, error_collector *errors) {
\t(void) fout;
\terrors->png_error_msg = "PNG support is disabled in this package";
\terrors->png_status = 1;
\trewind(fp);
\tdecompress_jpeg(fp, fout, errors);
}
''',
        )
        configure = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure, "umask 077", "umask 022")
        self.run(
            f'sh "{configure}" --host=aarch64-linux-ohos --prefix=/ '
            "'--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' "
            "'--libdir=${prefix}/lib' '--includedir=${prefix}/include' "
            "'--oldincludedir=${prefix}/include' "
            "--disable-silent-rules --disable-curl --disable-termlib "
            "--disable-doxygen-doc --disable-doxygen-html"
        )
        autotools = Autotools(self)
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSES/*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
