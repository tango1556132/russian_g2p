from argparse import ArgumentParser
import codecs
import os

import pymorphy2
from russian_tagsets import converters

from russian_g2p.Grapheme2Phoneme import Grapheme2Phoneme


class Lexicon(object):

    def __init__(self, phones):
        """ phones: list of strings, each being a phone """
        self.phone_set = set(self.make_position_independent(phones))

    # XSAMPA phones are 1-letter each, so 2-letter below represent 2 separate phones.
    CMU_to_XSAMPA_dict = {
        "'"   : "'",
        'AA'  : 'A',
        'AE'  : '{',
        'AH'  : 'V',  ##
        'AO'  : 'O',  ##
        'AW'  : 'aU',
        'AY'  : 'aI',
        'B'   : 'b',
        'CH'  : 'tS',
        'D'   : 'd',
        'DH'  : 'D',
        'EH'  : 'E',
        'ER'  : '3',
        'EY'  : 'eI',
        'F'   : 'f',
        'G'   : 'g',
        'HH'  : 'h',
        'IH'  : 'I',
        'IY'  : 'i',
        'JH'  : 'dZ',
        'K'   : 'k',
        'L'   : 'l',
        'M'   : 'm',
        'NG'  : 'N',
        'N'   : 'n',
        'OW'  : 'oU',
        'OY'  : 'OI', ##
        'P'   : 'p',
        'R'   : 'r',
        'SH'  : 'S',
        'S'   : 's',
        'TH'  : 'T',
        'T'   : 't',
        'UH'  : 'U',
        'UW'  : 'u',
        'V'   : 'v',
        'W'   : 'w',
        'Y'   : 'j',
        'ZH'  : 'Z',
        'Z'   : 'z',
    }
    CMU_to_XSAMPA_dict.update({'AX': '@'})
    del CMU_to_XSAMPA_dict["'"]
    XSAMPA_to_CMU_dict = { v: k for k,v in CMU_to_XSAMPA_dict.items() }  # FIXME: handle double-entries

    @classmethod
    def phones_cmu_to_xsampa_generic(cls, phones, lexicon_phones=None):
        new_phones = []
        for phone in phones:
            stress = False
            if phone.endswith('1'):
                phone = phone[:-1]
                stress = True
            elif phone.endswith(('0', '2')):
                phone = phone[:-1]
            phone = cls.CMU_to_XSAMPA_dict[phone]
            assert 1 <= len(phone) <= 2

            new_phone = ("'" if stress else '') + phone
            if (lexicon_phones is not None) and (new_phone in lexicon_phones):
                # Add entire possibly-2-letter phone
                new_phones.append(new_phone)
            else:
                # Add each individual 1-letter phone
                for match in re.finditer(r"('?).", new_phone):
                    new_phones.append(match.group(0))

        return new_phones

    def phones_cmu_to_xsampa(self, phones):
        return self.phones_cmu_to_xsampa_generic(phones, self.phone_set)

    @classmethod
    def make_position_dependent(cls, phones):
        if len(phones) == 0: return []
        elif len(phones) == 1: return [phones[0]+'_S']
        else: return [phones[0]+'_B'] + [phone+'_I' for phone in phones[1:-1]] + [phones[-1]+'_E']

    @classmethod
    def make_position_independent(cls, phones):
        return [re.sub(r'_[SBIE]', '', phone) for phone in phones]


def transcribe_words(source_words_list):
    bad_words = []
    transcriptions = []
    
    trans = Grapheme2Phoneme()
    lexicon = Lexicon()

    for word_unformated in source_words_list:
        word = word_unformated.replace("\u0301", "+")
        word = word.replace("о́", "o+")
        
        transcription = [word_unformated]
        for phone in trans.word_to_phonemes(word):
            xsampa_phone = lexicon.phones_cmu_to_xsampa(phone)
            transcription.append(xsampa_phone)
        print(transcription)
        transcriptions.append(transcription)
    return transcriptions, bad_words

    
    # n_words = len(source_words_list)
    # n_parts = 100
    # part_size = n_words // n_parts
    # while (part_size * n_parts) < n_words:
    #     part_size += 1
    # transcriptions = []
    # bad_words = []
    # to_ud2 = converters.converter('opencorpora-int', 'ud20')
    # morph = pymorphy2.MorphAnalyzer()
    # g2p = Grapheme2Phoneme(exception_for_nonaccented=True)
    # russian_letters = set('АаБбВвГгДдЕеЁёЖжЗзИиЙйКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЪъЫыЬьЭэЮюЯя')
    # russian_consonants = set('БбВвГгДдЖжЗзЙйКкЛлМмНнПпРрСсТтФфХхЦцЧчШшЩщЪъЬь')
    # part_counter = 0
    # for word_idx in range(len(source_words_list)):
    #     cur_word = source_words_list[word_idx].strip().lower()
    #     err_msg = 'Word {0} is wrong!'.format(word_idx)
    #     assert len(cur_word) > 0, err_msg + ' It is empty!'
    #     # assert set(cur_word) <= (russian_letters | {'-'}), \
    #     #     err_msg + ' "{0}" contains an inadmissible characters.'.format(cur_word)
    #     assert set(cur_word) != {'-'}, err_msg + ' It is empty!'
    #     if (len(cur_word) > 1) and (set(cur_word) <= russian_consonants):
    #         bad_words.append(cur_word)
    #     else:
    #         morpho_variants = set([to_ud2(str(it.tag)) for it in morph.parse(cur_word)])
    #         try:
    #             accentuation_variants = []
    #             variants_of_transcriptions = list(set(
    #                 filter(
    #                     lambda it2: len(it2) > 0,
    #                     map(
    #                         lambda it: tuple(g2p.word_to_phonemes(it)),
    #                         accentuation_variants
    #                     )
    #                 )
    #             ))
    #             if len(variants_of_transcriptions) > 0:
    #                 transcriptions.append((cur_word, ' '.join(variants_of_transcriptions[0])))
    #                 if len(variants_of_transcriptions) > 1:
    #                     for variant_idx in range(1, len(variants_of_transcriptions)):
    #                         transcriptions.append(('{0}({1})'.format(cur_word, variant_idx + 1),
    #                                                ' '.join(variants_of_transcriptions[variant_idx])))
    #             else:
    #                 bad_words.append(cur_word)
    #         except:
    #             bad_words.append(cur_word)
    #     if ((word_idx + 1) % part_size) == 0:
    #         part_counter += 1
    #         print('{0:.2%} of words have been processed...'.format(part_counter / float(n_parts)))
    # if part_counter < n_parts:
    #     print('100.00% of words have been processed...')
    # return transcriptions, bad_words


def main():
    parser = ArgumentParser()
    parser.add_argument('-s', '--src', dest='source_word_list', type=str, required=True,
                        help='Source file with words for which phonetical transcirptions will be calculated.')
    parser.add_argument('-d', '--dst', dest='destination_dictionary', type=str, required=True,
                        help='Destination file into which all words with their calculated transcriptions will be '
                             'written.')
    parser.add_argument('-b', '--bad', dest='bad_word_list', type=str, required=True,
                        help='Special file into which bad words will be written '
                             '(transcriptions for bad words cannot be calculated).')
    args = parser.parse_args()

    src_name = os.path.normpath(args.source_word_list)
    assert os.path.isfile(src_name), 'File "{0}" does not exist!'.format(src_name)

    dst_name = os.path.normpath(args.destination_dictionary)
    dst_dir = os.path.dirname(dst_name)
    if len(dst_dir) > 0:
        assert os.path.isdir(dst_dir), 'Directory "{0}" does not exist!'.format(dst_dir)

    bad_name = os.path.normpath(args.bad_word_list)
    bad_dir = os.path.dirname(bad_name)
    if len(bad_dir) > 0:
        assert os.path.isdir(bad_dir), 'Directory "{0}" does not exist!'.format(bad_dir)

    source_words = list()
    with codecs.open(src_name, mode='r',  encoding='utf-8', errors='ignore') as fp:
        cur_line = fp.readline()
        
        while len(cur_line) > 0:
            prep_line = cur_line.strip()
            if len(prep_line) > 0:
                source_words.append(prep_line)
            cur_line = fp.readline()
    assert len(source_words) > 0, 'The source word list "{0}" is empty!'.format(src_name)
    print('Source words have been successfully loaded...')

    transcriptions, bad_words = transcribe_words(sorted(source_words))
    with codecs.open(dst_name, mode='w', encoding='utf-8', errors='ignore') as fp:
        for cur in transcriptions:
            # write accented word
            for index, sound in enumerate(cur):
                fp.write('{0} '.format(sound))
            fp.write("\n")

            # write un-accented word
            word = cur[0]
            word = word.replace("\u0301", "+")
            # word = word.replace("о́", "o+")
            fp.write('{0} '.format(word))
            for index, sound in enumerate(cur):
                # skip word
                if index == 0:
                    continue 
                fp.write('{0} '.format(sound))
            fp.write("\n")


    if len(bad_words) > 0:
        with codecs.open(bad_name, mode='w', encoding='utf-8', errors='ignore') as fp:
            for cur in sorted(bad_words):
                fp.write('{0}\n'.format(cur))


if __name__ == '__main__':
    main()
