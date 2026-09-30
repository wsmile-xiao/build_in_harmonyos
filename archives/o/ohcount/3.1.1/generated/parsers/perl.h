
#line 1 "perl.rl"
// perl.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_PERL_PARSER_H
#define OHCOUNT_PERL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *PERL_LANG = LANG_PERL;

// the languages entities
const char *perl_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  PERL_SPACE = 0, PERL_COMMENT, PERL_STRING, PERL_ANY
};

/*****************************************************************************/


#line 28 "perl.h"
static const char _perl_actions[] = {
	0, 1, 2, 1, 10, 1, 11, 1, 
	13, 1, 14, 1, 15, 1, 16, 1, 
	17, 1, 20, 1, 22, 1, 23, 1, 
	24, 1, 25, 1, 26, 1, 27, 1, 
	29, 1, 30, 1, 31, 1, 32, 1, 
	33, 2, 0, 3, 2, 1, 23, 2, 
	2, 18, 2, 3, 12, 2, 6, 4, 
	2, 7, 4, 2, 8, 4, 2, 9, 
	4, 2, 11, 19, 2, 12, 21, 2, 
	14, 28, 2, 17, 3, 2, 17, 12, 
	2, 17, 14, 3, 1, 2, 18, 3, 
	6, 4, 23, 3, 7, 4, 2, 3, 
	8, 4, 2, 3, 9, 4, 2, 3, 
	17, 6, 4, 4, 6, 4, 1, 23, 
	4, 17, 0, 2, 12, 4, 17, 1, 
	3, 5, 4, 17, 6, 4, 3, 5, 
	7, 4, 1, 2, 18, 5, 8, 4, 
	1, 2, 18, 5, 9, 4, 1, 2, 
	18
};

static const char _perl_cond_offsets[] = {
	0, 0, 1, 2, 3, 4, 5, 6, 
	6, 6, 7, 8, 8, 8, 8, 8, 
	9, 10, 10, 10, 10, 10, 10, 11, 
	11, 11, 11, 13, 13, 14, 14, 15, 
	15, 16, 18, 20, 22, 24, 26, 28, 
	30, 32, 34
};

static const char _perl_cond_lengths[] = {
	0, 1, 1, 1, 1, 1, 1, 0, 
	0, 1, 1, 0, 0, 0, 0, 1, 
	1, 0, 0, 0, 0, 0, 1, 0, 
	0, 0, 2, 0, 1, 0, 1, 0, 
	1, 2, 2, 2, 2, 2, 2, 2, 
	2, 2, 0
};

static const short _perl_cond_keys[] = {
	61, 61, 61, 61, 61, 61, 61, 61, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 61, 61, 13, 13, 
	61, 61, 13, 13, 13, 13, 13, 13, 
	13, 13, 61, 61, 13, 13, 61, 61, 
	13, 13, 61, 61, 13, 13, 61, 61, 
	13, 13, 61, 61, 13, 13, 61, 61, 
	13, 13, 61, 61, 13, 13, 61, 61, 
	13, 13, 61, 61, 0
};

static const char _perl_cond_spaces[] = {
	1, 1, 1, 1, 0, 0, 0, 0, 
	0, 0, 1, 0, 1, 0, 0, 0, 
	0, 1, 0, 1, 0, 1, 0, 1, 
	0, 1, 0, 1, 0, 1, 0, 1, 
	0, 1, 0
};

static const short _perl_key_offsets[] = {
	0, 0, 6, 13, 20, 27, 39, 51, 
	54, 55, 67, 79, 82, 83, 88, 91, 
	103, 115, 118, 119, 122, 123, 124, 136, 
	139, 142, 146, 165, 167, 179, 182, 194, 
	199, 211, 226, 240, 254, 269, 284, 299, 
	315, 331, 347
};

static const short _perl_trans_keys[] = {
	317, 573, 0, 60, 62, 255, 99, 317, 
	573, 0, 60, 62, 255, 117, 317, 573, 
	0, 60, 62, 255, 116, 317, 573, 0, 
	60, 62, 255, 9, 10, 12, 32, 34, 
	92, 781, 1037, 0, 11, 14, 255, 9, 
	10, 12, 32, 34, 92, 781, 1037, 0, 
	11, 14, 255, 10, 12, 13, 10, 9, 
	10, 12, 32, 39, 92, 781, 1037, 0, 
	11, 14, 255, 9, 10, 12, 32, 39, 
	92, 781, 1037, 0, 11, 14, 255, 10, 
	12, 13, 10, 10, 47, 92, 12, 13, 
	10, 12, 13, 9, 10, 12, 32, 92, 
	96, 781, 1037, 0, 11, 14, 255, 9, 
	10, 12, 32, 92, 96, 781, 1037, 0, 
	11, 14, 255, 10, 12, 13, 10, 10, 
	12, 13, 10, 10, 32, 35, 317, 573, 
	0, 8, 9, 13, 14, 60, 62, 255, 
	32, 9, 13, 10, 12, 13, 65, 90, 
	97, 122, 9, 10, 12, 32, 34, 35, 
	39, 47, 96, 317, 573, 781, 1037, 0, 
	8, 14, 60, 62, 255, 9, 32, 9, 
	10, 12, 32, 34, 92, 781, 1037, 0, 
	11, 14, 255, 10, 12, 13, 9, 10, 
	12, 32, 39, 92, 781, 1037, 0, 11, 
	14, 255, 10, 47, 92, 12, 13, 9, 
	10, 12, 32, 92, 96, 781, 1037, 0, 
	11, 14, 255, 10, 12, 32, 317, 573, 
	781, 1037, 0, 8, 9, 11, 14, 60, 
	62, 255, 9, 10, 12, 32, 317, 573, 
	781, 1037, 0, 8, 14, 60, 62, 255, 
	9, 10, 12, 32, 317, 573, 781, 1037, 
	0, 8, 14, 60, 62, 255, 9, 10, 
	12, 32, 99, 317, 573, 781, 1037, 0, 
	8, 14, 60, 62, 255, 9, 10, 12, 
	32, 117, 317, 573, 781, 1037, 0, 8, 
	14, 60, 62, 255, 9, 10, 12, 32, 
	116, 317, 573, 781, 1037, 0, 8, 14, 
	60, 62, 255, 10, 12, 32, 99, 317, 
	573, 781, 1037, 0, 8, 9, 11, 14, 
	60, 62, 255, 10, 12, 32, 117, 317, 
	573, 781, 1037, 0, 8, 9, 11, 14, 
	60, 62, 255, 10, 12, 32, 116, 317, 
	573, 781, 1037, 0, 8, 9, 11, 14, 
	60, 62, 255, 10, 0
};

static const char _perl_single_lengths[] = {
	0, 2, 3, 3, 3, 8, 8, 1, 
	1, 8, 8, 1, 1, 3, 1, 8, 
	8, 1, 1, 1, 1, 1, 4, 1, 
	1, 0, 13, 2, 8, 1, 8, 3, 
	8, 7, 8, 8, 9, 9, 9, 8, 
	8, 8, 1
};

static const char _perl_range_lengths[] = {
	0, 2, 2, 2, 2, 2, 2, 1, 
	0, 2, 2, 1, 0, 1, 1, 2, 
	2, 1, 0, 1, 0, 0, 4, 1, 
	1, 2, 3, 0, 2, 1, 2, 1, 
	2, 4, 3, 3, 3, 3, 3, 4, 
	4, 4, 0
};

static const short _perl_index_offsets[] = {
	0, 0, 5, 11, 17, 23, 34, 45, 
	48, 50, 61, 72, 75, 77, 82, 85, 
	96, 107, 110, 112, 115, 117, 119, 128, 
	131, 134, 137, 154, 157, 168, 171, 182, 
	187, 198, 210, 222, 234, 247, 260, 273, 
	286, 299, 312
};

static const char _perl_indicies[] = {
	1, 2, 1, 1, 0, 3, 1, 2, 
	1, 1, 0, 4, 1, 2, 1, 1, 
	0, 5, 1, 2, 1, 1, 0, 8, 
	9, 9, 8, 10, 11, 12, 9, 7, 
	7, 6, 14, 15, 15, 14, 16, 17, 
	18, 15, 13, 13, 6, 6, 6, 7, 
	9, 6, 20, 21, 21, 20, 10, 22, 
	23, 21, 19, 19, 6, 25, 26, 26, 
	25, 27, 28, 29, 26, 24, 24, 6, 
	6, 6, 19, 21, 6, 6, 31, 32, 
	6, 30, 6, 6, 30, 34, 35, 35, 
	34, 36, 10, 37, 35, 33, 33, 6, 
	39, 40, 40, 39, 41, 42, 43, 40, 
	38, 38, 6, 6, 6, 33, 35, 6, 
	45, 45, 44, 47, 46, 48, 45, 50, 
	51, 49, 52, 49, 50, 49, 49, 45, 
	50, 50, 53, 54, 54, 51, 1, 1, 
	55, 57, 48, 48, 57, 58, 59, 60, 
	61, 62, 63, 64, 65, 66, 56, 56, 
	56, 45, 57, 57, 67, 8, 9, 9, 
	8, 10, 11, 12, 9, 7, 7, 68, 
	69, 69, 70, 20, 21, 21, 20, 10, 
	22, 23, 21, 19, 19, 68, 68, 31, 
	32, 68, 30, 34, 35, 35, 34, 36, 
	10, 37, 35, 33, 33, 68, 47, 47, 
	44, 72, 73, 74, 47, 72, 44, 72, 
	72, 69, 77, 78, 78, 77, 76, 80, 
	81, 78, 76, 76, 76, 79, 83, 47, 
	47, 83, 82, 84, 74, 47, 82, 82, 
	82, 69, 83, 47, 47, 83, 85, 82, 
	84, 74, 47, 82, 82, 82, 69, 83, 
	47, 47, 83, 86, 82, 84, 74, 47, 
	82, 82, 82, 69, 83, 47, 47, 83, 
	87, 82, 84, 74, 47, 82, 82, 82, 
	69, 47, 47, 44, 88, 72, 73, 74, 
	47, 72, 44, 72, 72, 69, 47, 47, 
	44, 89, 72, 73, 74, 47, 72, 44, 
	72, 72, 69, 47, 47, 44, 90, 72, 
	73, 74, 47, 72, 44, 72, 72, 69, 
	48, 91, 0
};

static const char _perl_trans_targs[] = {
	22, 1, 2, 3, 4, 22, 26, 5, 
	5, 6, 26, 7, 8, 5, 5, 6, 
	26, 7, 8, 9, 9, 10, 11, 12, 
	9, 9, 10, 26, 11, 12, 13, 26, 
	14, 15, 15, 16, 17, 18, 15, 15, 
	16, 17, 26, 18, 33, 0, 26, 34, 
	26, 22, 23, 24, 25, 22, 22, 22, 
	26, 27, 28, 29, 30, 31, 32, 26, 
	19, 21, 42, 26, 26, 26, 29, 26, 
	33, 39, 20, 26, 35, 35, 34, 26, 
	36, 20, 35, 35, 36, 37, 38, 35, 
	40, 41, 33, 26
};

static const char _perl_trans_actions[] = {
	39, 9, 9, 9, 9, 71, 29, 1, 
	0, 0, 83, 0, 0, 95, 59, 59, 
	133, 59, 59, 1, 0, 0, 0, 0, 
	91, 56, 56, 127, 56, 56, 0, 47, 
	0, 1, 0, 0, 0, 0, 99, 62, 
	62, 62, 139, 62, 15, 0, 27, 15, 
	65, 31, 7, 9, 80, 33, 35, 37, 
	68, 3, 112, 50, 112, 77, 112, 17, 
	41, 5, 5, 19, 25, 21, 0, 44, 
	74, 74, 0, 107, 122, 103, 103, 87, 
	122, 53, 74, 15, 74, 74, 74, 117, 
	74, 74, 117, 23
};

static const char _perl_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 11, 0, 
	0, 0, 11, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const char _perl_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 13, 0, 
	0, 0, 13, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0
};

static const short _perl_eof_trans[] = {
	0, 1, 1, 1, 1, 7, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 7, 
	7, 7, 7, 0, 47, 0, 0, 54, 
	55, 56, 0, 68, 69, 70, 69, 69, 
	69, 72, 76, 72, 72, 72, 72, 72, 
	72, 72, 92
};

static const int perl_start = 22;
static const int perl_first_final = 22;
static const int perl_error = 0;

static const int perl_en_perl_line = 26;
static const int perl_en_perl_entity = 22;


#line 123 "perl.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Perl code.
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
void parse_perl(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 304 "perl.h"
	{
	cs = perl_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 146 "perl.rl"
  cs = (count) ? perl_en_perl_line : perl_en_perl_entity;
  
#line 315 "perl.h"
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
	_acts = _perl_actions + _perl_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 16:
#line 1 "NONE"
	{ts = p;}
	break;
#line 337 "perl.h"
		}
	}

	_widec = (*p);
	_klen = _perl_cond_lengths[cs];
	_keys = _perl_cond_keys + (_perl_cond_offsets[cs]*2);
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
				switch ( _perl_cond_spaces[_perl_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(768 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
	case 1: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 75 "common.rl"

  p == buffer || *(p-1) == '\r' || *(p-1) == '\n' || *(p-1) == '\f'
 ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _perl_trans_keys + _perl_key_offsets[cs];
	_trans = _perl_index_offsets[cs];

	_klen = _perl_single_lengths[cs];
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

	_klen = _perl_range_lengths[cs];
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
	_trans = _perl_indicies[_trans];
_eof_trans:
	cs = _perl_trans_targs[_trans];

	if ( _perl_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _perl_actions + _perl_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 30 "common.rl"
	{
  inqueue = 1;
  if (callback_list_head) free_queue(); // free the current queue
  callback_list_head = NULL;
  callback_list_tail = NULL;
  // set backup variables
  last_line_start = line_start;
  last_line_contains_code = line_contains_code;
  last_whole_line_comment = whole_line_comment;
}
	break;
	case 1:
#line 41 "common.rl"
	{
  if (inqueue) {
    Callback *item;
    for (item = callback_list_head; item != NULL; item = item->next)
      callback(item->lang, item->entity, item->s, item->e, item->udata);
    free_queue();
    inqueue = 0;
  }
}
	break;
	case 2:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 3:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 4:
#line 31 "perl.rl"
	{
    switch(entity) {
    case PERL_SPACE:
      ls
      break;
    case PERL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PERL_LANG)
      break;
    case NEWLINE:
      std_newline(PERL_LANG)
    }
  }
	break;
	case 5:
#line 50 "perl.rl"
	{ {cs = 26;goto _again;} }
	break;
	case 6:
#line 52 "perl.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 7:
#line 62 "perl.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 8:
#line 72 "perl.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 9:
#line 82 "perl.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 10:
#line 98 "perl.rl"
	{ entity = PERL_SPACE; }
	break;
	case 11:
#line 101 "perl.rl"
	{ entity = NEWLINE;    }
	break;
	case 12:
#line 103 "perl.rl"
	{ entity = PERL_ANY;   }
	break;
	case 13:
#line 118 "perl.rl"
	{ entity = PERL_SPACE;   }
	break;
	case 14:
#line 119 "perl.rl"
	{ entity = PERL_COMMENT; }
	break;
	case 17:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 18:
#line 100 "perl.rl"
	{te = p+1;}
	break;
	case 19:
#line 31 "perl.rl"
	{te = p+1;{
    switch(entity) {
    case PERL_SPACE:
      ls
      break;
    case PERL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PERL_LANG)
      break;
    case NEWLINE:
      std_newline(PERL_LANG)
    }
  }}
	break;
	case 20:
#line 102 "perl.rl"
	{te = p+1;}
	break;
	case 21:
#line 31 "perl.rl"
	{te = p+1;{
    switch(entity) {
    case PERL_SPACE:
      ls
      break;
    case PERL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PERL_LANG)
      break;
    case NEWLINE:
      std_newline(PERL_LANG)
    }
  }}
	break;
	case 22:
#line 31 "perl.rl"
	{te = p;p--;{
    switch(entity) {
    case PERL_SPACE:
      ls
      break;
    case PERL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PERL_LANG)
      break;
    case NEWLINE:
      std_newline(PERL_LANG)
    }
  }}
	break;
	case 23:
#line 99 "perl.rl"
	{te = p;p--;}
	break;
	case 24:
#line 31 "perl.rl"
	{te = p;p--;{
    switch(entity) {
    case PERL_SPACE:
      ls
      break;
    case PERL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PERL_LANG)
      break;
    case NEWLINE:
      std_newline(PERL_LANG)
    }
  }}
	break;
	case 25:
#line 31 "perl.rl"
	{te = p;p--;{
    switch(entity) {
    case PERL_SPACE:
      ls
      break;
    case PERL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PERL_LANG)
      break;
    case NEWLINE:
      std_newline(PERL_LANG)
    }
  }}
	break;
	case 26:
#line 99 "perl.rl"
	{{p = ((te))-1;}}
	break;
	case 27:
#line 31 "perl.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case PERL_SPACE:
      ls
      break;
    case PERL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(PERL_LANG)
      break;
    case NEWLINE:
      std_newline(PERL_LANG)
    }
  }}
	break;
	case 28:
#line 108 "perl.rl"
	{te = p+1;{
    callback(PERL_LANG, perl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 29:
#line 121 "perl.rl"
	{te = p+1;}
	break;
	case 30:
#line 108 "perl.rl"
	{te = p;p--;{
    callback(PERL_LANG, perl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 31:
#line 108 "perl.rl"
	{te = p;p--;{
    callback(PERL_LANG, perl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 32:
#line 121 "perl.rl"
	{te = p;p--;}
	break;
	case 33:
#line 121 "perl.rl"
	{{p = ((te))-1;}}
	break;
#line 700 "perl.h"
		}
	}

_again:
	_acts = _perl_actions + _perl_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 15:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 713 "perl.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _perl_eof_trans[cs] > 0 ) {
		_trans = _perl_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 148 "perl.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(PERL_LANG) }
}

#endif

/*****************************************************************************/
