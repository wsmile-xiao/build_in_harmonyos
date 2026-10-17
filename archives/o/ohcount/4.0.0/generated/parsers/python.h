
#line 1 "python.rl"
// python.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_PYTHON_PARSER_H
#define OHCOUNT_PYTHON_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *PYTHON_LANG = LANG_PYTHON;

// the languages entities
const char *python_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  PYTHON_SPACE = 0, PYTHON_COMMENT, PYTHON_STRING, PYTHON_ANY
};

/*****************************************************************************/


#line 28 "python.h"
static const char _python_actions[] = {
	0, 1, 1, 1, 7, 1, 9, 1, 
	10, 1, 11, 1, 13, 1, 14, 1, 
	15, 1, 16, 1, 18, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 26, 1, 
	28, 1, 29, 1, 30, 1, 31, 1, 
	32, 2, 0, 19, 2, 1, 12, 2, 
	1, 18, 2, 3, 2, 2, 4, 2, 
	2, 5, 2, 2, 6, 7, 2, 8, 
	9, 2, 11, 20, 2, 12, 21, 2, 
	14, 27, 2, 17, 12, 2, 17, 14, 
	3, 3, 2, 1, 3, 4, 2, 1, 
	3, 5, 2, 1
};

static const char _python_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 1, 
	2, 3, 4, 4, 4, 4, 4, 5, 
	6, 7, 8, 8, 9, 10, 11, 11, 
	11, 11, 11, 11, 11, 11, 11, 11, 
	11, 12, 12, 12, 12, 12, 12, 12
};

static const char _python_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 1, 
	1, 1, 0, 0, 0, 0, 1, 1, 
	1, 1, 0, 1, 1, 1, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0, 0, 0
};

static const short _python_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _python_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0
};

static const char _python_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 5, 6, 
	7, 8, 9, 11, 16, 19, 20, 31, 
	42, 53, 64, 65, 70, 73, 74, 85, 
	96, 107, 118, 119, 130, 141, 153, 154, 
	155, 162, 165, 166, 167, 170, 171, 172, 
	174, 188, 190, 191, 192, 195, 196, 198
};

static const short _python_trans_keys[] = {
	34, 34, 34, 34, 39, 39, 39, 39, 
	42, 42, 47, 10, 34, 92, 12, 13, 
	10, 12, 13, 34, 9, 10, 12, 32, 
	34, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 34, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 34, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 34, 269, 525, 0, 11, 14, 255, 
	10, 10, 39, 92, 12, 13, 10, 12, 
	13, 39, 9, 10, 12, 32, 39, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 39, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 39, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 39, 
	269, 525, 0, 11, 14, 255, 10, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 269, 
	525, 0, 11, 14, 255, 9, 10, 12, 
	32, 42, 47, 269, 525, 0, 11, 14, 
	255, 10, 10, 32, 34, 35, 39, 47, 
	9, 13, 32, 9, 13, 34, 34, 10, 
	12, 13, 39, 39, 42, 47, 9, 10, 
	12, 32, 34, 35, 39, 47, 269, 525, 
	0, 8, 14, 255, 9, 32, 34, 34, 
	10, 12, 13, 39, 42, 47, 10, 0
};

static const char _python_single_lengths[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 2, 3, 1, 1, 7, 7, 
	7, 7, 1, 3, 1, 1, 7, 7, 
	7, 7, 1, 7, 7, 8, 1, 1, 
	5, 1, 1, 1, 1, 1, 1, 2, 
	10, 2, 1, 1, 1, 1, 2, 1
};

static const char _python_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 1, 1, 0, 2, 2, 
	2, 2, 0, 1, 1, 0, 2, 2, 
	2, 2, 0, 2, 2, 2, 0, 0, 
	1, 1, 0, 0, 1, 0, 0, 0, 
	2, 0, 0, 0, 1, 0, 0, 0
};

static const short _python_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 10, 12, 
	14, 16, 18, 21, 26, 29, 31, 41, 
	51, 61, 71, 73, 78, 81, 83, 93, 
	103, 113, 123, 125, 135, 145, 156, 158, 
	160, 167, 170, 172, 174, 177, 179, 181, 
	184, 197, 200, 202, 204, 207, 209, 212
};

static const char _python_indicies[] = {
	1, 0, 2, 1, 3, 1, 4, 1, 
	5, 0, 6, 5, 7, 5, 8, 5, 
	10, 9, 10, 11, 9, 12, 14, 15, 
	12, 13, 12, 12, 13, 17, 16, 18, 
	19, 19, 18, 20, 21, 19, 17, 17, 
	12, 23, 24, 24, 23, 25, 26, 24, 
	22, 22, 12, 18, 19, 19, 18, 27, 
	21, 19, 17, 17, 12, 18, 19, 19, 
	18, 28, 21, 19, 17, 17, 12, 19, 
	12, 12, 14, 30, 12, 29, 12, 12, 
	29, 32, 31, 33, 34, 34, 33, 35, 
	36, 34, 32, 32, 12, 38, 39, 39, 
	38, 40, 41, 39, 37, 37, 12, 33, 
	34, 34, 33, 42, 36, 34, 32, 32, 
	12, 33, 34, 34, 33, 43, 36, 34, 
	32, 32, 12, 34, 12, 45, 46, 46, 
	45, 47, 48, 46, 44, 44, 12, 50, 
	51, 51, 50, 52, 53, 51, 49, 49, 
	12, 45, 46, 46, 45, 47, 54, 48, 
	46, 44, 44, 12, 46, 12, 55, 56, 
	58, 59, 60, 61, 62, 58, 57, 58, 
	58, 63, 65, 64, 11, 66, 66, 66, 
	60, 67, 64, 11, 66, 9, 60, 64, 
	69, 55, 55, 69, 70, 71, 72, 73, 
	74, 75, 68, 68, 56, 69, 69, 76, 
	79, 78, 43, 80, 80, 80, 81, 83, 
	82, 44, 84, 77, 55, 85, 0
};

static const char _python_trans_targs[] = {
	32, 2, 3, 4, 35, 6, 7, 8, 
	38, 9, 10, 32, 40, 11, 40, 12, 
	11, 14, 14, 15, 16, 18, 14, 14, 
	15, 16, 18, 17, 43, 19, 20, 19, 
	22, 22, 23, 24, 26, 22, 22, 23, 
	24, 26, 25, 40, 27, 27, 28, 29, 
	30, 27, 27, 28, 29, 30, 40, 40, 
	0, 32, 33, 34, 36, 37, 39, 32, 
	32, 1, 32, 5, 40, 41, 42, 44, 
	45, 46, 31, 47, 40, 40, 11, 13, 
	40, 44, 19, 21, 44, 40
};

static const char _python_trans_actions[] = {
	39, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 71, 29, 0, 41, 0, 
	62, 1, 0, 0, 1, 0, 88, 56, 
	56, 88, 56, 1, 1, 0, 0, 59, 
	1, 0, 0, 1, 0, 84, 53, 53, 
	84, 53, 1, 47, 1, 0, 0, 1, 
	0, 80, 50, 50, 80, 50, 19, 65, 
	0, 31, 11, 77, 13, 77, 77, 33, 
	37, 13, 35, 13, 68, 7, 74, 44, 
	74, 74, 9, 9, 21, 27, 5, 0, 
	23, 0, 3, 0, 1, 25
};

static const char _python_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 0, 0, 0, 0
};

static const char _python_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	17, 0, 0, 0, 0, 0, 0, 0, 
	17, 0, 0, 0, 0, 0, 0, 0
};

static const short _python_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 0, 
	0, 64, 65, 67, 67, 65, 67, 65, 
	0, 77, 78, 81, 81, 78, 78, 86
};

static const int python_start = 32;
static const int python_first_final = 32;
static const int python_error = 0;

static const int python_en_python_line = 40;
static const int python_en_python_entity = 32;


#line 112 "python.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Python code.
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
void parse_python(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 255 "python.h"
	{
	cs = python_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 135 "python.rl"
  cs = (count) ? python_en_python_line : python_en_python_entity;
  
#line 266 "python.h"
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
	_acts = _python_actions + _python_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 16:
#line 1 "NONE"
	{ts = p;}
	break;
#line 288 "python.h"
		}
	}

	_widec = (*p);
	_klen = _python_cond_lengths[cs];
	_keys = _python_cond_keys + (_python_cond_offsets[cs]*2);
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
				switch ( _python_cond_spaces[_python_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _python_trans_keys + _python_key_offsets[cs];
	_trans = _python_index_offsets[cs];

	_klen = _python_single_lengths[cs];
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

	_klen = _python_range_lengths[cs];
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
	_trans = _python_indicies[_trans];
_eof_trans:
	cs = _python_trans_targs[_trans];

	if ( _python_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _python_actions + _python_trans_actions[_trans];
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
#line 31 "python.rl"
	{
    switch(entity) {
    case PYTHON_SPACE:
      ls
      break;
    case PYTHON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PYTHON_LANG)
      break;
    case NEWLINE:
      std_newline(PYTHON_LANG)
    }
  }
	break;
	case 3:
#line 50 "python.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 58 "python.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 66 "python.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 76 "python.rl"
	{ p--; }
	break;
	case 7:
#line 76 "python.rl"
	{ p--; }
	break;
	case 8:
#line 79 "python.rl"
	{ p--; }
	break;
	case 9:
#line 79 "python.rl"
	{ p--; }
	break;
	case 10:
#line 84 "python.rl"
	{ entity = PYTHON_SPACE; }
	break;
	case 11:
#line 87 "python.rl"
	{ entity = NEWLINE;      }
	break;
	case 12:
#line 88 "python.rl"
	{ entity = PYTHON_ANY;   }
	break;
	case 13:
#line 107 "python.rl"
	{ entity = PYTHON_SPACE;   }
	break;
	case 14:
#line 108 "python.rl"
	{ entity = PYTHON_COMMENT; }
	break;
	case 17:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 18:
#line 85 "python.rl"
	{te = p+1;}
	break;
	case 19:
#line 86 "python.rl"
	{te = p+1;}
	break;
	case 20:
#line 31 "python.rl"
	{te = p+1;{
    switch(entity) {
    case PYTHON_SPACE:
      ls
      break;
    case PYTHON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PYTHON_LANG)
      break;
    case NEWLINE:
      std_newline(PYTHON_LANG)
    }
  }}
	break;
	case 21:
#line 31 "python.rl"
	{te = p+1;{
    switch(entity) {
    case PYTHON_SPACE:
      ls
      break;
    case PYTHON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PYTHON_LANG)
      break;
    case NEWLINE:
      std_newline(PYTHON_LANG)
    }
  }}
	break;
	case 22:
#line 31 "python.rl"
	{te = p;p--;{
    switch(entity) {
    case PYTHON_SPACE:
      ls
      break;
    case PYTHON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PYTHON_LANG)
      break;
    case NEWLINE:
      std_newline(PYTHON_LANG)
    }
  }}
	break;
	case 23:
#line 85 "python.rl"
	{te = p;p--;}
	break;
	case 24:
#line 31 "python.rl"
	{te = p;p--;{
    switch(entity) {
    case PYTHON_SPACE:
      ls
      break;
    case PYTHON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PYTHON_LANG)
      break;
    case NEWLINE:
      std_newline(PYTHON_LANG)
    }
  }}
	break;
	case 25:
#line 31 "python.rl"
	{te = p;p--;{
    switch(entity) {
    case PYTHON_SPACE:
      ls
      break;
    case PYTHON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PYTHON_LANG)
      break;
    case NEWLINE:
      std_newline(PYTHON_LANG)
    }
  }}
	break;
	case 26:
#line 31 "python.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case PYTHON_SPACE:
      ls
      break;
    case PYTHON_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PYTHON_LANG)
      break;
    case NEWLINE:
      std_newline(PYTHON_LANG)
    }
  }}
	break;
	case 27:
#line 93 "python.rl"
	{te = p+1;{
    callback(PYTHON_LANG, python_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 28:
#line 110 "python.rl"
	{te = p+1;}
	break;
	case 29:
#line 93 "python.rl"
	{te = p;p--;{
    callback(PYTHON_LANG, python_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 30:
#line 93 "python.rl"
	{te = p;p--;{
    callback(PYTHON_LANG, python_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 31:
#line 110 "python.rl"
	{te = p;p--;}
	break;
	case 32:
#line 110 "python.rl"
	{{p = ((te))-1;}}
	break;
#line 624 "python.h"
		}
	}

_again:
	_acts = _python_actions + _python_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 15:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 637 "python.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _python_eof_trans[cs] > 0 ) {
		_trans = _python_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 137 "python.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(PYTHON_LANG) }
}

#endif

/*****************************************************************************/
