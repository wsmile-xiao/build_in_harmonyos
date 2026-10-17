
#line 1 "modelica.rl"
// modelica.rl written by Martin Sjölund. martin.sjolund<att>liu<dott>se

/************************* Required for every parser *************************/
#ifndef OHCOUNT_MODELICA_PARSER_H
#define OHCOUNT_MODELICA_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *MODELICA_LANG = LANG_MODELICA;

// the languages entities
const char *modelica_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  MODELICA_SPACE = 0, MODELICA_COMMENT, MODELICA_STRING, MODELICA_ANY
};

/*****************************************************************************/


#line 28 "modelica.h"
static const char _modelica_actions[] = {
	0, 1, 1, 1, 5, 1, 6, 1, 
	7, 1, 8, 1, 10, 1, 11, 1, 
	12, 1, 13, 1, 14, 1, 15, 1, 
	17, 1, 21, 1, 22, 1, 23, 1, 
	24, 1, 25, 1, 26, 1, 29, 1, 
	30, 1, 31, 1, 32, 1, 33, 1, 
	34, 2, 0, 8, 2, 0, 13, 2, 
	1, 11, 2, 3, 2, 2, 6, 18, 
	2, 7, 9, 2, 9, 20, 2, 11, 
	27, 2, 16, 9, 2, 16, 11, 3, 
	0, 8, 19, 3, 0, 13, 28, 3, 
	3, 2, 1, 3, 3, 2, 11, 3, 
	4, 2, 8, 3, 4, 2, 13, 3, 
	16, 0, 13, 4, 3, 2, 1, 11, 
	4, 4, 2, 0, 8, 4, 4, 2, 
	0, 13, 4, 16, 0, 8, 9, 5, 
	4, 2, 0, 8, 19, 5, 4, 2, 
	0, 13, 28
};

static const char _modelica_cond_offsets[] = {
	0, 0, 1, 2, 2, 3, 4, 5, 
	5, 6, 7, 7, 8, 9, 10, 10, 
	10, 10, 10, 11, 11, 11, 11, 12, 
	12, 13, 13, 13, 13
};

static const char _modelica_cond_lengths[] = {
	0, 1, 1, 0, 1, 1, 1, 0, 
	1, 1, 0, 1, 1, 1, 0, 0, 
	0, 0, 1, 0, 0, 0, 1, 0, 
	1, 0, 0, 0, 0
};

static const short _modelica_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 0
};

static const char _modelica_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0
};

static const char _modelica_key_offsets[] = {
	0, 0, 12, 24, 25, 36, 47, 59, 
	60, 72, 84, 85, 96, 107, 119, 120, 
	121, 131, 134, 146, 148, 151, 158, 179, 
	181, 193, 195, 198, 205
};

static const short _modelica_trans_keys[] = {
	9, 10, 12, 32, 34, 92, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	34, 9, 10, 12, 32, 42, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	42, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 42, 47, 269, 525, 0, 
	11, 14, 255, 10, 9, 10, 12, 32, 
	34, 92, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 34, 92, 269, 525, 
	0, 11, 14, 255, 34, 9, 10, 12, 
	32, 42, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 42, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 42, 
	47, 269, 525, 0, 11, 14, 255, 10, 
	10, 32, 34, 47, 95, 9, 13, 65, 
	90, 97, 122, 32, 9, 13, 9, 10, 
	12, 32, 34, 92, 269, 525, 0, 11, 
	14, 255, 42, 47, 10, 12, 13, 95, 
	48, 57, 65, 90, 97, 122, 9, 10, 
	12, 32, 34, 47, 95, 269, 525, 0, 
	8, 14, 64, 65, 90, 91, 96, 97, 
	122, 123, 255, 9, 32, 9, 10, 12, 
	32, 34, 92, 269, 525, 0, 11, 14, 
	255, 42, 47, 10, 12, 13, 95, 48, 
	57, 65, 90, 97, 122, 10, 0
};

static const char _modelica_single_lengths[] = {
	0, 8, 8, 1, 7, 7, 8, 1, 
	8, 8, 1, 7, 7, 8, 1, 1, 
	4, 1, 8, 2, 1, 1, 9, 2, 
	8, 2, 1, 1, 1
};

static const char _modelica_range_lengths[] = {
	0, 2, 2, 0, 2, 2, 2, 0, 
	2, 2, 0, 2, 2, 2, 0, 0, 
	3, 1, 2, 0, 1, 3, 6, 0, 
	2, 0, 1, 3, 0
};

static const char _modelica_index_offsets[] = {
	0, 0, 11, 22, 24, 34, 44, 55, 
	57, 68, 79, 81, 91, 101, 112, 114, 
	116, 124, 127, 138, 141, 144, 149, 165, 
	168, 179, 182, 185, 190
};

static const char _modelica_indicies[] = {
	2, 3, 4, 2, 5, 6, 1, 4, 
	1, 1, 0, 8, 9, 10, 8, 11, 
	12, 7, 10, 7, 7, 0, 1, 0, 
	14, 15, 15, 14, 16, 17, 15, 13, 
	13, 0, 19, 20, 20, 19, 21, 22, 
	20, 18, 18, 0, 14, 15, 15, 14, 
	16, 23, 17, 15, 13, 13, 0, 15, 
	0, 26, 27, 28, 26, 29, 30, 25, 
	28, 25, 25, 24, 32, 33, 34, 32, 
	35, 36, 31, 34, 31, 31, 24, 25, 
	24, 38, 39, 39, 38, 40, 41, 39, 
	37, 37, 24, 43, 44, 44, 43, 45, 
	46, 44, 42, 42, 24, 38, 39, 39, 
	38, 40, 47, 41, 39, 37, 37, 24, 
	39, 24, 48, 49, 51, 52, 53, 54, 
	51, 54, 54, 50, 51, 51, 55, 2, 
	3, 4, 2, 5, 6, 1, 4, 1, 
	1, 56, 13, 57, 56, 58, 58, 59, 
	54, 54, 54, 54, 60, 62, 48, 48, 
	62, 63, 64, 65, 66, 67, 61, 61, 
	65, 61, 65, 61, 49, 62, 62, 68, 
	26, 27, 28, 26, 29, 30, 25, 28, 
	25, 25, 69, 37, 70, 69, 71, 71, 
	72, 74, 74, 74, 74, 73, 48, 75, 
	0
};

static const char _modelica_trans_targs[] = {
	16, 1, 1, 2, 2, 16, 3, 1, 
	1, 2, 2, 16, 3, 4, 4, 5, 
	6, 7, 4, 4, 5, 6, 7, 16, 
	22, 8, 8, 9, 9, 22, 10, 8, 
	8, 9, 9, 22, 10, 11, 11, 12, 
	13, 14, 11, 11, 12, 13, 14, 22, 
	22, 0, 16, 17, 18, 19, 21, 16, 
	16, 20, 16, 20, 16, 22, 23, 24, 
	25, 27, 15, 28, 22, 22, 26, 22, 
	26, 22, 27, 22
};

static const char _modelica_trans_actions[] = {
	47, 52, 17, 17, 52, 83, 17, 117, 
	99, 99, 117, 133, 99, 55, 13, 13, 
	55, 13, 107, 91, 91, 107, 91, 70, 
	35, 49, 9, 9, 49, 79, 9, 112, 
	95, 95, 112, 127, 95, 1, 0, 0, 
	1, 0, 87, 58, 58, 87, 58, 23, 
	61, 0, 37, 11, 103, 76, 15, 39, 
	45, 55, 41, 13, 43, 67, 3, 122, 
	73, 64, 5, 5, 25, 33, 1, 27, 
	0, 31, 7, 29
};

static const char _modelica_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	19, 0, 0, 0, 0, 0, 19, 0, 
	0, 0, 0, 0, 0
};

static const char _modelica_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	21, 0, 0, 0, 0, 0, 21, 0, 
	0, 0, 0, 0, 0
};

static const char _modelica_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	25, 25, 25, 25, 25, 25, 25, 0, 
	0, 56, 57, 57, 59, 61, 0, 69, 
	70, 70, 72, 74, 76
};

static const int modelica_start = 16;
static const int modelica_first_final = 16;
static const int modelica_error = 0;

static const int modelica_en_modelica_line = 22;
static const int modelica_en_modelica_entity = 16;


#line 102 "modelica.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Modelica code.
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
void parse_modelica(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init
  
#line 239 "modelica.h"
	{
	cs = modelica_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 124 "modelica.rl"
  cs = (count) ? modelica_en_modelica_line : modelica_en_modelica_entity;
  
#line 250 "modelica.h"
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
	_acts = _modelica_actions + _modelica_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 15:
#line 1 "NONE"
	{ts = p;}
	break;
#line 272 "modelica.h"
		}
	}

	_widec = (*p);
	_klen = _modelica_cond_lengths[cs];
	_keys = _modelica_cond_keys + (_modelica_cond_offsets[cs]*2);
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
				switch ( _modelica_cond_spaces[_modelica_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _modelica_trans_keys + _modelica_key_offsets[cs];
	_trans = _modelica_index_offsets[cs];

	_klen = _modelica_single_lengths[cs];
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

	_klen = _modelica_range_lengths[cs];
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
	_trans = _modelica_indicies[_trans];
_eof_trans:
	cs = _modelica_trans_targs[_trans];

	if ( _modelica_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _modelica_actions + _modelica_trans_actions[_trans];
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
#line 31 "modelica.rl"
	{
    switch(entity) {
    case MODELICA_SPACE:
      ls
      break;
    case MODELICA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODELICA_LANG)
      break;
    case NEWLINE:
      std_newline(MODELICA_LANG)
    }
  }
	break;
	case 3:
#line 51 "modelica.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 61 "modelica.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 68 "modelica.rl"
	{ entity = MODELICA_SPACE; }
	break;
	case 6:
#line 70 "modelica.rl"
	{ entity = NEWLINE;   }
	break;
	case 7:
#line 71 "modelica.rl"
	{ entity = MODELICA_ANY; }
	break;
	case 8:
#line 72 "modelica.rl"
	{ entity = MODELICA_ANY; }
	break;
	case 9:
#line 73 "modelica.rl"
	{ entity = MODELICA_ANY;   }
	break;
	case 10:
#line 96 "modelica.rl"
	{ entity = MODELICA_SPACE;   }
	break;
	case 11:
#line 97 "modelica.rl"
	{ entity = MODELICA_COMMENT; }
	break;
	case 12:
#line 98 "modelica.rl"
	{ entity = MODELICA_ANY; }
	break;
	case 13:
#line 99 "modelica.rl"
	{ entity = MODELICA_ANY; }
	break;
	case 16:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 17:
#line 69 "modelica.rl"
	{te = p+1;}
	break;
	case 18:
#line 31 "modelica.rl"
	{te = p+1;{
    switch(entity) {
    case MODELICA_SPACE:
      ls
      break;
    case MODELICA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODELICA_LANG)
      break;
    case NEWLINE:
      std_newline(MODELICA_LANG)
    }
  }}
	break;
	case 19:
#line 31 "modelica.rl"
	{te = p+1;{
    switch(entity) {
    case MODELICA_SPACE:
      ls
      break;
    case MODELICA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODELICA_LANG)
      break;
    case NEWLINE:
      std_newline(MODELICA_LANG)
    }
  }}
	break;
	case 20:
#line 31 "modelica.rl"
	{te = p+1;{
    switch(entity) {
    case MODELICA_SPACE:
      ls
      break;
    case MODELICA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODELICA_LANG)
      break;
    case NEWLINE:
      std_newline(MODELICA_LANG)
    }
  }}
	break;
	case 21:
#line 31 "modelica.rl"
	{te = p;p--;{
    switch(entity) {
    case MODELICA_SPACE:
      ls
      break;
    case MODELICA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODELICA_LANG)
      break;
    case NEWLINE:
      std_newline(MODELICA_LANG)
    }
  }}
	break;
	case 22:
#line 69 "modelica.rl"
	{te = p;p--;}
	break;
	case 23:
#line 31 "modelica.rl"
	{te = p;p--;{
    switch(entity) {
    case MODELICA_SPACE:
      ls
      break;
    case MODELICA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODELICA_LANG)
      break;
    case NEWLINE:
      std_newline(MODELICA_LANG)
    }
  }}
	break;
	case 24:
#line 31 "modelica.rl"
	{te = p;p--;{
    switch(entity) {
    case MODELICA_SPACE:
      ls
      break;
    case MODELICA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODELICA_LANG)
      break;
    case NEWLINE:
      std_newline(MODELICA_LANG)
    }
  }}
	break;
	case 25:
#line 31 "modelica.rl"
	{te = p;p--;{
    switch(entity) {
    case MODELICA_SPACE:
      ls
      break;
    case MODELICA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODELICA_LANG)
      break;
    case NEWLINE:
      std_newline(MODELICA_LANG)
    }
  }}
	break;
	case 26:
#line 31 "modelica.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case MODELICA_SPACE:
      ls
      break;
    case MODELICA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MODELICA_LANG)
      break;
    case NEWLINE:
      std_newline(MODELICA_LANG)
    }
  }}
	break;
	case 27:
#line 78 "modelica.rl"
	{te = p+1;{
    callback(MODELICA_LANG, modelica_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 28:
#line 78 "modelica.rl"
	{te = p+1;{
    callback(MODELICA_LANG, modelica_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 29:
#line 100 "modelica.rl"
	{te = p+1;}
	break;
	case 30:
#line 78 "modelica.rl"
	{te = p;p--;{
    callback(MODELICA_LANG, modelica_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 31:
#line 78 "modelica.rl"
	{te = p;p--;{
    callback(MODELICA_LANG, modelica_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 32:
#line 78 "modelica.rl"
	{te = p;p--;{
    callback(MODELICA_LANG, modelica_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 33:
#line 100 "modelica.rl"
	{te = p;p--;}
	break;
	case 34:
#line 100 "modelica.rl"
	{{p = ((te))-1;}}
	break;
#line 645 "modelica.h"
		}
	}

_again:
	_acts = _modelica_actions + _modelica_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 14:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 658 "modelica.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _modelica_eof_trans[cs] > 0 ) {
		_trans = _modelica_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 126 "modelica.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(MODELICA_LANG) }
}

#endif

/*****************************************************************************/
