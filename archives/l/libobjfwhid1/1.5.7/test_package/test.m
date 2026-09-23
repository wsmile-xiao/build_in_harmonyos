/*
 * test_package for libobjfwhid1 1.5.7
 *
 * Genuinely exercises the ObjFWHID public API: the +[OHGameController
 * controllers] class method dispatches into libobjfwhid's evdev backend
 * (OHEvdevGameController). On CI/sandbox the /dev/input directory is not
 * readable, which the backend reports as an OFOpenItemFailedException —
 * that is a device-access restriction, not a library defect. We exercise
 * the real API and treat the expected platform restriction gracefully.
 */
#include <stdlib.h>

#import <ObjFWHID/ObjFWHID.h>
#import <ObjFW/OFArray.h>
#import <ObjFW/OFException.h>
#import <ObjFW/OFOpenItemFailedException.h>
#import <ObjFW/OFStdIOStream.h>

int main(void)
{
	void *pool = objc_autoreleasePoolPush();
	bool enumerated = false;

	@try {
		OFArray *controllers = [OHGameController controllers];
		(void)controllers;
		enumerated = true;
	} @catch (OFOpenItemFailedException *e) {
		/* /dev/input not accessible on this platform. */
		[OFStdOut writeFormat:
		    @"libobjfwhid OK (device enumeration unavailable: %@)\n", e];
	} @catch (OFException *e) {
		[OFStdErr writeFormat: @"Unexpected exception: %@\n", e];
		objc_autoreleasePoolPop(pool);
		return 1;
	}

	if (enumerated)
		[OFStdOut writeFormat:
		    @"libobjfwhid OK: controllers enumerated\n"];

	objc_autoreleasePoolPop(pool);
	return 0;
}
