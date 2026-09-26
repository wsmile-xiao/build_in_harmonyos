
#line 1 "groovy.rl"
// groovy.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_GROOVY_PARSER_H
#define OHCOUNT_GROOVY_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *GROOVY_LANG = LANG_GROOVY;

// the languages entities
const char *groovy_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  GROOVY_SPACE = 0, GROOVY_COMMENT, GROOVY_STRING, GROOVY_ANY
};

/*****************************************************************************/


#line 28 "groovy.h"
static const char _groovy_actions[] = {
	0, 1, 0, 1, 1, 1, 7, 1, 
	8, 1, 10, 1, 11, 1, 12, 1, 
	13, 1, 15, 1, 16, 1, 19, 1, 
	20, 1, 21, 1, 22, 1, 23, 1, 
	24, 1, 26, 1, 27, 1, 28, 1, 
	29, 1, 30, 1, 31, 2, 3, 2, 
	2, 4, 2, 2, 5, 2, 2, 6, 
	2, 2, 8, 17, 2, 9, 18, 2, 
	11, 25, 2, 14, 1, 2, 14, 9, 
	2, 14, 11, 3, 3, 2, 1, 3, 
	3, 2, 20, 3, 4, 2, 1, 3, 
	5, 2, 0, 3, 5, 2, 16, 3, 
	6, 2, 0, 3, 6, 2, 16, 3, 
	14, 0, 9, 4, 14, 3, 2, 1
	
};

static const char _groovy_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 1, 1, 
	1, 1, 1, 2, 2, 2, 2, 3, 
	4, 5, 5, 5, 5, 5, 5, 5, 
	5, 6, 6, 7, 7, 7, 7, 7, 
	7, 8, 8, 8
};

static const char _groovy_cond_lengths[] = {
	0, 0, 0, 0, 0, 1, 0, 0, 
	0, 0, 1, 0, 0, 0, 1, 1, 
	1, 0, 0, 0, 0, 0, 0, 0, 
	1, 0, 1, 0, 0, 0, 0, 0, 
	1, 0, 0, 0
};

static const short _groovy_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _groovy_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0
};

static const char _groovy_key_offsets[] = {
	0, 0, 1, 3, 4, 8, 16, 20, 
	21, 26, 30, 38, 42, 43, 48, 59, 
	70, 82, 83, 84, 85, 89, 92, 94, 
	98, 105, 108, 121, 123, 127, 131, 133, 
	139, 150, 156, 162
};

static const short _groovy_trans_keys[] = {
	42, 42, 47, 10, 9, 32, 34, 92, 
	10, 12, 269, 525, 0, 11, 14, 255, 
	9, 32, 34, 92, 10, 9, 10, 32, 
	34, 92, 9, 32, 39, 92, 10, 12, 
	269, 525, 0, 11, 14, 255, 9, 32, 
	39, 92, 10, 9, 10, 32, 39, 92, 
	9, 10, 12, 32, 42, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 42, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 42, 47, 269, 525, 0, 11, 
	14, 255, 10, 10, 10, 32, 47, 9, 
	13, 32, 9, 13, 42, 47, 10, 92, 
	12, 13, 92, 269, 525, 0, 12, 14, 
	255, 92, 12, 13, 9, 10, 12, 32, 
	34, 39, 47, 269, 525, 0, 8, 14, 
	255, 9, 32, 9, 32, 34, 92, 9, 
	32, 39, 92, 42, 47, 9, 10, 32, 
	92, 12, 13, 9, 10, 12, 32, 92, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	32, 92, 12, 13, 9, 10, 32, 92, 
	12, 13, 10, 0
};

static const char _groovy_single_lengths[] = {
	0, 1, 2, 1, 4, 4, 4, 1, 
	5, 4, 4, 4, 1, 5, 7, 7, 
	8, 1, 1, 1, 2, 1, 2, 2, 
	3, 1, 9, 2, 4, 4, 2, 4, 
	7, 4, 4, 1
};

static const char _groovy_range_lengths[] = {
	0, 0, 0, 0, 0, 2, 0, 0, 
	0, 0, 2, 0, 0, 0, 2, 2, 
	2, 0, 0, 0, 1, 1, 0, 1, 
	2, 1, 2, 0, 0, 0, 0, 1, 
	2, 1, 1, 0
};

static const char _groovy_index_offsets[] = {
	0, 0, 2, 5, 7, 12, 19, 24, 
	26, 32, 37, 44, 49, 51, 57, 67, 
	77, 88, 90, 92, 94, 98, 101, 104, 
	108, 114, 117, 129, 132, 137, 142, 145, 
	151, 161, 167, 173
};

static const char _groovy_indicies[] = {
	2, 1, 2, 3, 1, 5, 4, 8, 
	8, 9, 10, 7, 11, 11, 12, 13, 
	7, 7, 6, 15, 15, 16, 17, 14, 
	11, 6, 15, 18, 15, 16, 17, 14, 
	20, 20, 9, 21, 19, 22, 22, 23, 
	24, 19, 19, 6, 26, 26, 27, 28, 
	25, 22, 6, 26, 29, 26, 27, 28, 
	25, 31, 32, 32, 31, 33, 34, 32, 
	30, 30, 6, 36, 37, 37, 36, 38, 
	39, 37, 35, 35, 6, 31, 32, 32, 
	31, 33, 40, 34, 32, 30, 30, 6, 
	32, 6, 42, 41, 43, 44, 46, 47, 
	46, 45, 46, 46, 48, 1, 5, 49, 
	50, 51, 50, 5, 51, 52, 53, 5, 
	5, 50, 51, 50, 5, 55, 43, 43, 
	55, 56, 57, 58, 59, 60, 54, 54, 
	44, 55, 55, 61, 8, 8, 9, 10, 
	7, 20, 20, 9, 21, 19, 30, 63, 
	62, 65, 64, 65, 66, 64, 63, 65, 
	42, 42, 65, 66, 67, 68, 63, 63, 
	64, 71, 69, 71, 72, 69, 70, 71, 
	42, 71, 72, 69, 70, 43, 73, 0
};

static const char _groovy_trans_targs[] = {
	20, 1, 2, 20, 20, 23, 26, 4, 
	4, 26, 5, 6, 7, 8, 4, 4, 
	26, 5, 6, 9, 9, 10, 11, 12, 
	13, 9, 9, 26, 10, 11, 14, 14, 
	15, 16, 17, 14, 14, 15, 16, 17, 
	26, 26, 33, 26, 0, 20, 21, 22, 
	20, 20, 20, 24, 3, 25, 26, 27, 
	28, 29, 30, 19, 35, 26, 26, 31, 
	26, 31, 32, 18, 34, 26, 31, 31, 
	32, 26
};

static const char _groovy_trans_actions[] = {
	43, 11, 11, 63, 41, 11, 31, 1, 
	0, 19, 0, 0, 0, 0, 95, 54, 
	99, 54, 95, 1, 0, 0, 0, 0, 
	0, 87, 51, 91, 51, 87, 3, 0, 
	0, 3, 0, 83, 48, 48, 83, 48, 
	17, 29, 0, 57, 0, 33, 9, 72, 
	35, 39, 37, 72, 11, 11, 60, 5, 
	103, 103, 69, 7, 7, 21, 27, 3, 
	23, 0, 66, 0, 0, 79, 75, 45, 
	107, 25
};

static const char _groovy_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 13, 0, 0, 0, 
	0, 0, 13, 0, 0, 0, 0, 0, 
	0, 0, 0, 0
};

static const char _groovy_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 15, 0, 0, 0, 
	0, 0, 15, 0, 0, 0, 0, 0, 
	0, 0, 0, 0
};

static const char _groovy_eof_trans[] = {
	0, 1, 1, 5, 7, 7, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 7, 
	7, 7, 42, 0, 0, 49, 50, 51, 
	51, 51, 0, 62, 63, 63, 63, 65, 
	65, 70, 70, 74
};

static const int groovy_start = 20;
static const int groovy_first_final = 20;
static const int groovy_error = 0;

static const int groovy_en_groovy_line = 26;
static const int groovy_en_groovy_entity = 20;


#line 113 "groovy.rl"


/* Parses a string buffer with Groovy code.
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
void parse_groovy(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 235 "groovy.h"
	{
	cs = groovy_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 134 "groovy.rl"
  cs = (count) ? groovy_en_groovy_line : groovy_en_groovy_entity;
  
#line 246 "groovy.h"
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
	_acts = _groovy_actions + _groovy_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = p;}
	break;
#line 268 "groovy.h"
		}
	}

	_widec = (*p);
	_klen = _groovy_cond_lengths[cs];
	_keys = _groovy_cond_keys + (_groovy_cond_offsets[cs]*2);
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
				switch ( _groovy_cond_spaces[_groovy_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _groovy_trans_keys + _groovy_key_offsets[cs];
	_trans = _groovy_index_offsets[cs];

	_klen = _groovy_single_lengths[cs];
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

	_klen = _groovy_range_lengths[cs];
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
	_trans = _groovy_indicies[_trans];
_eof_trans:
	cs = _groovy_trans_targs[_trans];

	if ( _groovy_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _groovy_actions + _groovy_trans_actions[_trans];
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
#line 31 "groovy.rl"
	{
    switch(entity) {
    case GROOVY_SPACE:
      ls
      break;
    case GROOVY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GROOVY_LANG)
      break;
    case NEWLINE:
      std_newline(GROOVY_LANG)
    }
  }
	break;
	case 3:
#line 49 "groovy.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 57 "groovy.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 67 "groovy.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 77 "groovy.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 88 "groovy.rl"
	{ entity = GROOVY_SPACE; }
	break;
	case 8:
#line 91 "groovy.rl"
	{ entity = NEWLINE;      }
	break;
	case 9:
#line 92 "groovy.rl"
	{ entity = GROOVY_ANY;   }
	break;
	case 10:
#line 108 "groovy.rl"
	{ entity = GROOVY_SPACE;   }
	break;
	case 11:
#line 109 "groovy.rl"
	{ entity = GROOVY_COMMENT; }
	break;
	case 14:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 15:
#line 89 "groovy.rl"
	{te = p+1;}
	break;
	case 16:
#line 90 "groovy.rl"
	{te = p+1;}
	break;
	case 17:
#line 31 "groovy.rl"
	{te = p+1;{
    switch(entity) {
    case GROOVY_SPACE:
      ls
      break;
    case GROOVY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GROOVY_LANG)
      break;
    case NEWLINE:
      std_newline(GROOVY_LANG)
    }
  }}
	break;
	case 18:
#line 31 "groovy.rl"
	{te = p+1;{
    switch(entity) {
    case GROOVY_SPACE:
      ls
      break;
    case GROOVY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GROOVY_LANG)
      break;
    case NEWLINE:
      std_newline(GROOVY_LANG)
    }
  }}
	break;
	case 19:
#line 31 "groovy.rl"
	{te = p;p--;{
    switch(entity) {
    case GROOVY_SPACE:
      ls
      break;
    case GROOVY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GROOVY_LANG)
      break;
    case NEWLINE:
      std_newline(GROOVY_LANG)
    }
  }}
	break;
	case 20:
#line 89 "groovy.rl"
	{te = p;p--;}
	break;
	case 21:
#line 31 "groovy.rl"
	{te = p;p--;{
    switch(entity) {
    case GROOVY_SPACE:
      ls
      break;
    case GROOVY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GROOVY_LANG)
      break;
    case NEWLINE:
      std_newline(GROOVY_LANG)
    }
  }}
	break;
	case 22:
#line 31 "groovy.rl"
	{te = p;p--;{
    switch(entity) {
    case GROOVY_SPACE:
      ls
      break;
    case GROOVY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GROOVY_LANG)
      break;
    case NEWLINE:
      std_newline(GROOVY_LANG)
    }
  }}
	break;
	case 23:
#line 89 "groovy.rl"
	{{p = ((te))-1;}}
	break;
	case 24:
#line 31 "groovy.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case GROOVY_SPACE:
      ls
      break;
    case GROOVY_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(GROOVY_LANG)
      break;
    case NEWLINE:
      std_newline(GROOVY_LANG)
    }
  }}
	break;
	case 25:
#line 97 "groovy.rl"
	{te = p+1;{
    callback(GROOVY_LANG, groovy_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 26:
#line 111 "groovy.rl"
	{te = p+1;}
	break;
	case 27:
#line 97 "groovy.rl"
	{te = p;p--;{
    callback(GROOVY_LANG, groovy_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 28:
#line 97 "groovy.rl"
	{te = p;p--;{
    callback(GROOVY_LANG, groovy_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 29:
#line 111 "groovy.rl"
	{te = p;p--;}
	break;
	case 30:
#line 97 "groovy.rl"
	{{p = ((te))-1;}{
    callback(GROOVY_LANG, groovy_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 31:
#line 111 "groovy.rl"
	{{p = ((te))-1;}}
	break;
#line 603 "groovy.h"
		}
	}

_again:
	_acts = _groovy_actions + _groovy_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 616 "groovy.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _groovy_eof_trans[cs] > 0 ) {
		_trans = _groovy_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 136 "groovy.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(GROOVY_LANG) }
}

#endif
