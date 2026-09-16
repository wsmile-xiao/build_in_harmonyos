/*
 * test_package smoke test for libsvgtiny 0.1.8
 *
 * Exercises the public C API of the library (R34: must actually call the
 * package's API, not just print a string):
 *   - svgtiny_create   (allocate a diagram)
 *   - svgtiny_parse    (parse an inline SVG buffer through libdom XML binding)
 *   - svgtiny_free     (release the diagram)
 *
 * The inline SVG holds a <rect> and a <circle>, so after a successful parse
 * the diagram must report at least 2 shapes and a non-zero canvas size.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <svgtiny.h>

int main(void)
{
	static const char svg[] =
		"<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"50\">"
		"<rect x=\"1\" y=\"2\" width=\"40\" height=\"20\" fill=\"#ff0000\"/>"
		"<circle cx=\"70\" cy=\"25\" r=\"15\" fill=\"green\"/></svg>";
	struct svgtiny_diagram *diagram;
	svgtiny_code code;
	int ret = 1;

	diagram = svgtiny_create();
	if (diagram == NULL) {
		fprintf(stderr, "svgtiny_create failed\n");
		return 1;
	}

	code = svgtiny_parse(diagram, svg, strlen(svg), "test", 100, 50);
	if (code != svgtiny_OK) {
		fprintf(stderr, "svgtiny_parse failed: code=%d line=%u msg=%s\n",
				code, diagram->error_line,
				diagram->error_message ? diagram->error_message : "(null)");
		goto done;
	}

	/* width/height are int in struct svgtiny_diagram (svgtiny.h); the
	 * explicit casts make the %d conversion unambiguous. */
	printf("parsed: %u shapes, %dx%d canvas\n",
			diagram->shape_count, (int)diagram->width, (int)diagram->height);

	if (diagram->shape_count < 2 || diagram->width <= 0 ||
			diagram->height <= 0) {
		fprintf(stderr, "unexpected result: shape_count=%u width=%d height=%d\n",
				diagram->shape_count, (int)diagram->width,
				(int)diagram->height);
		goto done;
	}

	printf("libsvgtiny API OK\n");
	ret = 0;

done:
	svgtiny_free(diagram);
	return ret;
}
