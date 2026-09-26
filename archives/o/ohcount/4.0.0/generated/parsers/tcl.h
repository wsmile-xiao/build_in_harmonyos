
#line 1 "tcl.rl"
// tcl.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_TCL_PARSER_H
#define OHCOUNT_TCL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *TCL_LANG = LANG_TCL;

// the languages entities
const char *tcl_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  TCL_SPACE = 0, TCL_COMMENT, TCL_STRING, TCL_ANY
};

/*****************************************************************************/


#line 28 "tcl.h"
static const char _tcl_actions[] = {
	0, 1, 0, 1, 1, 1, 5, 1, 
	6, 1, 8, 1, 9, 1, 10, 1, 
	11, 1, 13, 1, 16, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 21, 1, 
	22, 1, 23, 1, 24, 1, 25, 2, 
	1, 7, 2, 3, 2, 2, 4, 2, 
	2, 6, 14, 2, 7, 15, 2, 12, 
	1, 2, 12, 9, 3, 3, 2, 1, 
	3, 3, 2, 17, 3, 4, 2, 0, 
	3, 4, 2, 13, 3, 12, 0, 7, 
	4, 12, 3, 2, 1
};

static const char _tcl_cond_offsets[] = {
	0, 0, 0, 0, 1, 1, 1, 1, 
	1, 1, 1, 1, 1, 2, 2, 3, 
	3, 3, 3, 4, 4, 4
};

static const char _tcl_cond_lengths[] = {
	0, 0, 0, 1, 0, 0, 0, 0, 
	0, 0, 0, 0, 1, 0, 1, 0, 
	0, 0, 1, 0, 0, 0
};

static const short _tcl_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _tcl_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _tcl_key_offsets[] = {
	0, 0, 1, 8, 16, 23, 24, 31, 
	32, 33, 37, 40, 44, 51, 54, 66, 
	68, 75, 81, 92, 98, 104
};

static const short _tcl_trans_keys[] = {
	10, 9, 10, 32, 34, 92, 12, 13, 
	10, 12, 269, 525, 0, 11, 14, 255, 
	9, 10, 32, 34, 92, 12, 13, 10, 
	9, 10, 32, 34, 92, 12, 13, 10, 
	10, 32, 35, 9, 13, 32, 9, 13, 
	10, 92, 12, 13, 92, 269, 525, 0, 
	12, 14, 255, 92, 12, 13, 9, 10, 
	12, 32, 34, 35, 269, 525, 0, 8, 
	14, 255, 9, 32, 9, 10, 32, 34, 
	92, 12, 13, 9, 10, 32, 92, 12, 
	13, 9, 10, 12, 32, 92, 269, 525, 
	0, 11, 14, 255, 9, 10, 32, 92, 
	12, 13, 9, 10, 32, 92, 12, 13, 
	10, 0
};

static const char _tcl_single_lengths[] = {
	0, 1, 5, 4, 5, 1, 5, 1, 
	1, 2, 1, 2, 3, 1, 8, 2, 
	5, 4, 7, 4, 4, 1
};

static const char _tcl_range_lengths[] = {
	0, 0, 1, 2, 1, 0, 1, 0, 
	0, 1, 1, 1, 2, 1, 2, 0, 
	1, 1, 2, 1, 1, 0
};

static const char _tcl_index_offsets[] = {
	0, 0, 2, 9, 16, 23, 25, 32, 
	34, 36, 40, 43, 47, 53, 56, 67, 
	70, 77, 83, 93, 99, 105
};

static const char _tcl_indicies[] = {
	1, 0, 4, 2, 4, 5, 6, 2, 
	3, 7, 7, 8, 9, 3, 3, 2, 
	11, 2, 11, 12, 13, 2, 10, 7, 
	2, 11, 7, 11, 12, 13, 2, 10, 
	15, 14, 16, 17, 19, 1, 19, 18, 
	19, 19, 20, 21, 22, 21, 1, 22, 
	23, 24, 1, 1, 21, 22, 21, 1, 
	26, 16, 16, 26, 27, 28, 29, 30, 
	25, 25, 17, 26, 26, 31, 4, 32, 
	4, 5, 6, 32, 3, 35, 33, 35, 
	36, 33, 34, 35, 15, 15, 35, 36, 
	37, 38, 34, 34, 33, 41, 39, 41, 
	42, 39, 40, 41, 15, 41, 42, 39, 
	40, 16, 43, 0
};

static const char _tcl_trans_targs[] = {
	9, 11, 14, 2, 2, 14, 3, 4, 
	5, 6, 2, 2, 14, 3, 14, 19, 
	14, 0, 9, 10, 9, 9, 12, 1, 
	13, 14, 15, 16, 17, 8, 21, 14, 
	14, 14, 17, 17, 18, 7, 20, 14, 
	17, 17, 18, 14
};

static const char _tcl_trans_actions[] = {
	37, 11, 29, 1, 0, 17, 0, 0, 
	0, 0, 68, 45, 72, 45, 27, 0, 
	48, 0, 31, 9, 33, 35, 57, 11, 
	11, 51, 5, 76, 39, 7, 7, 19, 
	25, 21, 3, 0, 54, 0, 0, 64, 
	60, 42, 80, 23
};

static const char _tcl_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 13, 0, 0, 0, 0, 13, 0, 
	0, 0, 0, 0, 0, 0
};

static const char _tcl_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 15, 0, 0, 0, 0, 15, 0, 
	0, 0, 0, 0, 0, 0
};

static const char _tcl_eof_trans[] = {
	0, 1, 3, 3, 3, 3, 3, 15, 
	0, 0, 21, 22, 22, 22, 0, 32, 
	33, 34, 34, 40, 40, 44
};

static const int tcl_start = 9;
static const int tcl_first_final = 9;
static const int tcl_error = 0;

static const int tcl_en_tcl_line = 14;
static const int tcl_en_tcl_entity = 9;


#line 89 "tcl.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Tcl code.
 *
 * @param *buffer The string to parse.
 * @param length The length of the string to parse.
 * @param count Integer flag specifying whether or not to count lines. If yes,
 *   uses the Ragel machine optimized for counting. Otherwise uses the Ragel
 *   machine optimized for returning entity positions.
 * @param *callback Callback function. If count is set, callback is called for
 *   every line of code, comment, or blank with 'lcode', 'lcomment', and
 *   'lblank' respectively. Otherwise callback is called for each entity found.
 */
void parse_tcl(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 190 "tcl.h"
	{
	cs = tcl_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 112 "tcl.rl"
  cs = (count) ? tcl_en_tcl_line : tcl_en_tcl_entity;
  
#line 201 "tcl.h"
	{
	int _klen;
	unsigned int _trans;
	short _widec;
	const char *_acts;
	unsigned int _nacts;
	const short *_keys;

	if ( p == pe )
		goto _test_eof;
	if ( cs == 0 )
		goto _out;
_resume:
	_acts = _tcl_actions + _tcl_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = p;}
	break;
#line 223 "tcl.h"
		}
	}

	_widec = (*p);
	_klen = _tcl_cond_lengths[cs];
	_keys = _tcl_cond_keys + (_tcl_cond_offsets[cs]*2);
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				switch ( _tcl_cond_spaces[_tcl_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _tcl_trans_keys + _tcl_key_offsets[cs];
	_trans = _tcl_index_offsets[cs];

	_klen = _tcl_single_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + _klen - 1;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + ((_upper-_lower) >> 1);
			if ( _widec < *_mid )
				_upper = _mid - 1;
			else if ( _widec > *_mid )
				_lower = _mid + 1;
			else {
				_trans += (unsigned int)(_mid - _keys);
				goto _match;
			}
		}
		_keys += _klen;
		_trans += _klen;
	}

	_klen = _tcl_range_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				_trans += (unsigned int)((_mid - _keys)>>1);
				goto _match;
			}
		}
		_trans += _klen;
	}

_match:
	_trans = _tcl_indicies[_trans];
_eof_trans:
	cs = _tcl_trans_targs[_trans];

	if ( _tcl_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _tcl_actions + _tcl_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 1:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 2:
#line 31 "tcl.rl"
	{
    switch(entity) {
    case TCL_SPACE:
      ls
      break;
    case TCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TCL_LANG)
      break;
    case NEWLINE:
      std_newline(TCL_LANG)
    }
  }
	break;
	case 3:
#line 49 "tcl.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 58 "tcl.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 68 "tcl.rl"
	{ entity = TCL_SPACE; }
	break;
	case 6:
#line 71 "tcl.rl"
	{ entity = NEWLINE;   }
	break;
	case 7:
#line 72 "tcl.rl"
	{ entity = TCL_ANY;   }
	break;
	case 8:
#line 84 "tcl.rl"
	{ entity = TCL_SPACE;   }
	break;
	case 9:
#line 85 "tcl.rl"
	{ entity = TCL_COMMENT; }
	break;
	case 12:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 13:
#line 70 "tcl.rl"
	{te = p+1;}
	break;
	case 14:
#line 31 "tcl.rl"
	{te = p+1;{
    switch(entity) {
    case TCL_SPACE:
      ls
      break;
    case TCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TCL_LANG)
      break;
    case NEWLINE:
      std_newline(TCL_LANG)
    }
  }}
	break;
	case 15:
#line 31 "tcl.rl"
	{te = p+1;{
    switch(entity) {
    case TCL_SPACE:
      ls
      break;
    case TCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TCL_LANG)
      break;
    case NEWLINE:
      std_newline(TCL_LANG)
    }
  }}
	break;
	case 16:
#line 31 "tcl.rl"
	{te = p;p--;{
    switch(entity) {
    case TCL_SPACE:
      ls
      break;
    case TCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TCL_LANG)
      break;
    case NEWLINE:
      std_newline(TCL_LANG)
    }
  }}
	break;
	case 17:
#line 69 "tcl.rl"
	{te = p;p--;}
	break;
	case 18:
#line 31 "tcl.rl"
	{te = p;p--;{
    switch(entity) {
    case TCL_SPACE:
      ls
      break;
    case TCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TCL_LANG)
      break;
    case NEWLINE:
      std_newline(TCL_LANG)
    }
  }}
	break;
	case 19:
#line 31 "tcl.rl"
	{te = p;p--;{
    switch(entity) {
    case TCL_SPACE:
      ls
      break;
    case TCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TCL_LANG)
      break;
    case NEWLINE:
      std_newline(TCL_LANG)
    }
  }}
	break;
	case 20:
#line 69 "tcl.rl"
	{{p = ((te))-1;}}
	break;
	case 21:
#line 31 "tcl.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case TCL_SPACE:
      ls
      break;
    case TCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TCL_LANG)
      break;
    case NEWLINE:
      std_newline(TCL_LANG)
    }
  }}
	break;
	case 22:
#line 87 "tcl.rl"
	{te = p+1;}
	break;
	case 23:
#line 77 "tcl.rl"
	{te = p;p--;{
    callback(TCL_LANG, tcl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 77 "tcl.rl"
	{te = p;p--;{
    callback(TCL_LANG, tcl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 77 "tcl.rl"
	{{p = ((te))-1;}{
    callback(TCL_LANG, tcl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 528 "tcl.h"
		}
	}

_again:
	_acts = _tcl_actions + _tcl_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 541 "tcl.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _tcl_eof_trans[cs] > 0 ) {
		_trans = _tcl_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 114 "tcl.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(TCL_LANG) }
}

#endif

/*****************************************************************************/
