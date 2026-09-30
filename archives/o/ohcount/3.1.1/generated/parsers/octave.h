
#line 1 "octave.rl"
// octave.rl based on Mitchell Foral's matlab.rl, modified my Jason Riedy <jason@acm.org>

/************************* Required for every parser *************************/
#ifndef OHCOUNT_OCTAVE_PARSER_H
#define OHCOUNT_OCTAVE_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *OCTAVE_LANG = LANG_OCTAVE;

// the languages entities
const char *octave_entities[] = {
  "space", "comment", "string", "any",
};

// constants associated with the entities
enum {
  OCTAVE_SPACE = 0, OCTAVE_COMMENT, OCTAVE_STRING, OCTAVE_ANY
};

/*****************************************************************************/


#line 28 "octave.h"
static const char _octave_actions[] = {
	0, 1, 0, 1, 1, 1, 5, 1, 
	6, 1, 9, 1, 10, 1, 11, 1, 
	12, 1, 14, 1, 15, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	24, 1, 25, 1, 26, 1, 27, 1, 
	28, 2, 1, 7, 2, 3, 1, 2, 
	4, 2, 2, 6, 16, 2, 7, 17, 
	2, 8, 10, 2, 10, 23, 2, 13, 
	7, 2, 13, 10, 3, 4, 2, 0, 
	3, 13, 0, 7
};

static const char _octave_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 2, 3, 3, 3, 3, 3, 3, 
	3, 3, 3, 3, 3, 3, 4, 4, 
	4, 4, 4, 4, 4
};

static const char _octave_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 1, 0, 0, 
	0, 0, 0, 0, 0
};

static const short _octave_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	0
};

static const char _octave_cond_spaces[] = {
	0, 0, 0, 0, 0
};

static const char _octave_key_offsets[] = {
	0, 0, 1, 3, 4, 5, 10, 13, 
	24, 35, 47, 48, 53, 56, 57, 58, 
	59, 65, 68, 71, 72, 73, 88, 90, 
	95, 98, 99, 104, 105
};

static const short _octave_trans_keys[] = {
	37, 37, 125, 46, 123, 10, 34, 92, 
	12, 13, 10, 12, 13, 9, 10, 12, 
	32, 37, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 37, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 37, 
	125, 269, 525, 0, 11, 14, 255, 10, 
	10, 39, 92, 12, 13, 10, 12, 13, 
	46, 123, 10, 32, 35, 37, 46, 9, 
	13, 32, 9, 13, 10, 12, 13, 123, 
	46, 9, 10, 12, 32, 34, 35, 37, 
	39, 46, 269, 525, 0, 8, 14, 255, 
	9, 32, 10, 34, 92, 12, 13, 10, 
	12, 13, 123, 10, 39, 92, 12, 13, 
	46, 10, 0
};

static const char _octave_single_lengths[] = {
	0, 1, 2, 1, 1, 3, 1, 7, 
	7, 8, 1, 3, 1, 1, 1, 1, 
	4, 1, 1, 1, 1, 11, 2, 3, 
	1, 1, 3, 1, 1
};

static const char _octave_range_lengths[] = {
	0, 0, 0, 0, 0, 1, 1, 2, 
	2, 2, 0, 1, 1, 0, 0, 0, 
	1, 1, 1, 0, 0, 2, 0, 1, 
	1, 0, 1, 0, 0
};

static const char _octave_index_offsets[] = {
	0, 0, 2, 5, 7, 9, 14, 17, 
	27, 37, 48, 50, 55, 58, 60, 62, 
	64, 70, 73, 76, 78, 80, 94, 97, 
	102, 105, 107, 112, 114
};

static const char _octave_indicies[] = {
	2, 1, 2, 3, 1, 4, 0, 0, 
	5, 6, 8, 9, 6, 7, 6, 6, 
	7, 11, 12, 12, 11, 13, 14, 12, 
	10, 10, 6, 16, 17, 17, 16, 18, 
	19, 17, 15, 15, 6, 11, 12, 12, 
	11, 13, 20, 14, 12, 10, 10, 6, 
	12, 6, 6, 8, 22, 6, 21, 6, 
	6, 21, 23, 6, 6, 24, 25, 26, 
	28, 29, 30, 31, 28, 27, 28, 28, 
	32, 33, 33, 29, 1, 5, 35, 34, 
	37, 25, 25, 37, 38, 39, 40, 41, 
	42, 43, 44, 36, 36, 26, 37, 37, 
	45, 46, 8, 9, 46, 7, 47, 47, 
	48, 49, 24, 46, 8, 22, 46, 21, 
	50, 46, 25, 51, 0
};

static const char _octave_trans_targs[] = {
	16, 1, 2, 16, 4, 18, 21, 5, 
	21, 6, 7, 7, 8, 9, 10, 7, 
	7, 8, 9, 10, 21, 11, 12, 14, 
	24, 21, 0, 16, 17, 18, 19, 20, 
	16, 16, 16, 3, 21, 22, 23, 24, 
	25, 26, 27, 15, 28, 21, 21, 21, 
	24, 7, 13, 21
};

static const char _octave_trans_actions[] = {
	39, 11, 11, 59, 11, 56, 29, 0, 
	19, 0, 1, 0, 0, 1, 0, 68, 
	47, 47, 68, 47, 17, 0, 0, 0, 
	44, 50, 0, 31, 9, 11, 65, 65, 
	33, 35, 37, 11, 53, 5, 72, 41, 
	62, 72, 62, 7, 7, 21, 27, 23, 
	0, 3, 0, 25
};

static const char _octave_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 0, 0, 13, 0, 0, 
	0, 0, 0, 0, 0
};

static const char _octave_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 0, 15, 0, 0, 
	0, 0, 0, 0, 0
};

static const char _octave_eof_trans[] = {
	0, 1, 1, 1, 1, 7, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 0, 
	0, 33, 34, 35, 35, 0, 46, 47, 
	48, 47, 47, 47, 52
};

static const int octave_start = 16;
static const int octave_first_final = 16;
static const int octave_error = 0;

static const int octave_en_octave_line = 21;
static const int octave_en_octave_entity = 16;


#line 91 "octave.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with OCTAVE code.
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
void parse_octave(char *buffer, int length, int count,
                  void (*callback) (const char *lang, const char *entity, int s,
                                    int e, void *udata),
                  void *userdata
  ) {
  init

  
#line 201 "octave.h"
	{
	cs = octave_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 114 "octave.rl"
  cs = (count) ? octave_en_octave_line : octave_en_octave_entity;
  
#line 212 "octave.h"
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
	_acts = _octave_actions + _octave_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 12:
#line 1 "NONE"
	{ts = p;}
	break;
#line 234 "octave.h"
		}
	}

	_widec = (*p);
	_klen = _octave_cond_lengths[cs];
	_keys = _octave_cond_keys + (_octave_cond_offsets[cs]*2);
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
				switch ( _octave_cond_spaces[_octave_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _octave_trans_keys + _octave_key_offsets[cs];
	_trans = _octave_index_offsets[cs];

	_klen = _octave_single_lengths[cs];
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

	_klen = _octave_range_lengths[cs];
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
	_trans = _octave_indicies[_trans];
_eof_trans:
	cs = _octave_trans_targs[_trans];

	if ( _octave_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _octave_actions + _octave_trans_actions[_trans];
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
#line 31 "octave.rl"
	{
    switch(entity) {
    case OCTAVE_SPACE:
      ls
      break;
    case OCTAVE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCTAVE_LANG)
      break;
    case NEWLINE:
      std_newline(OCTAVE_LANG)
    }
  }
	break;
	case 3:
#line 50 "octave.rl"
	{ p--; }
	break;
	case 4:
#line 53 "octave.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 66 "octave.rl"
	{ entity = OCTAVE_SPACE; }
	break;
	case 6:
#line 69 "octave.rl"
	{ entity = NEWLINE;      }
	break;
	case 7:
#line 70 "octave.rl"
	{ entity = OCTAVE_ANY;   }
	break;
	case 8:
#line 80 "octave.rl"
	{ p--; }
	break;
	case 9:
#line 86 "octave.rl"
	{ entity = OCTAVE_SPACE;   }
	break;
	case 10:
#line 87 "octave.rl"
	{ entity = OCTAVE_COMMENT; }
	break;
	case 13:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 14:
#line 67 "octave.rl"
	{te = p+1;}
	break;
	case 15:
#line 68 "octave.rl"
	{te = p+1;}
	break;
	case 16:
#line 31 "octave.rl"
	{te = p+1;{
    switch(entity) {
    case OCTAVE_SPACE:
      ls
      break;
    case OCTAVE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCTAVE_LANG)
      break;
    case NEWLINE:
      std_newline(OCTAVE_LANG)
    }
  }}
	break;
	case 17:
#line 31 "octave.rl"
	{te = p+1;{
    switch(entity) {
    case OCTAVE_SPACE:
      ls
      break;
    case OCTAVE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCTAVE_LANG)
      break;
    case NEWLINE:
      std_newline(OCTAVE_LANG)
    }
  }}
	break;
	case 18:
#line 31 "octave.rl"
	{te = p;p--;{
    switch(entity) {
    case OCTAVE_SPACE:
      ls
      break;
    case OCTAVE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCTAVE_LANG)
      break;
    case NEWLINE:
      std_newline(OCTAVE_LANG)
    }
  }}
	break;
	case 19:
#line 67 "octave.rl"
	{te = p;p--;}
	break;
	case 20:
#line 31 "octave.rl"
	{te = p;p--;{
    switch(entity) {
    case OCTAVE_SPACE:
      ls
      break;
    case OCTAVE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCTAVE_LANG)
      break;
    case NEWLINE:
      std_newline(OCTAVE_LANG)
    }
  }}
	break;
	case 21:
#line 31 "octave.rl"
	{te = p;p--;{
    switch(entity) {
    case OCTAVE_SPACE:
      ls
      break;
    case OCTAVE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCTAVE_LANG)
      break;
    case NEWLINE:
      std_newline(OCTAVE_LANG)
    }
  }}
	break;
	case 22:
#line 31 "octave.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case OCTAVE_SPACE:
      ls
      break;
    case OCTAVE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(OCTAVE_LANG)
      break;
    case NEWLINE:
      std_newline(OCTAVE_LANG)
    }
  }}
	break;
	case 23:
#line 75 "octave.rl"
	{te = p+1;{
    callback(OCTAVE_LANG, octave_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 24:
#line 89 "octave.rl"
	{te = p+1;}
	break;
	case 25:
#line 75 "octave.rl"
	{te = p;p--;{
    callback(OCTAVE_LANG, octave_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 26:
#line 75 "octave.rl"
	{te = p;p--;{
    callback(OCTAVE_LANG, octave_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 27:
#line 89 "octave.rl"
	{te = p;p--;}
	break;
	case 28:
#line 89 "octave.rl"
	{{p = ((te))-1;}}
	break;
#line 554 "octave.h"
		}
	}

_again:
	_acts = _octave_actions + _octave_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 567 "octave.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _octave_eof_trans[cs] > 0 ) {
		_trans = _octave_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 116 "octave.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(OCTAVE_LANG) }
}

#endif

/*****************************************************************************/
