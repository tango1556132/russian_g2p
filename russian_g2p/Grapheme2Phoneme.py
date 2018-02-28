import codecs
import copy
import os
import re
import warnings

from russian_g2p import RulesForGraphemes


class Grapheme2Phoneme:
    def __init__(self):
        self.__re_for_phrase_split = None

        self.__silence_name = 'sil'

        self.__russian_phonemes_set = {'U0', 'U', 'O0', 'O', 'A0', 'A', 'E0', 'E', 'Y0', 'Y', 'I0', 'I',
                                       'K0', 'K', 'H0', 'H', 'G0', 'G', 'J0', 'CH0', 'SH0', 'SH', 'ZH',
                                       'R0', 'R', 'T0', 'T', 'TS', 'S0', 'S', 'D0', 'D', 'Z0', 'Z', 'N0', 'N',
                                       'L0', 'L', 'P0', 'P', 'F0', 'F', 'B0', 'B', 'V0', 'V', 'M0', 'M',
                                       'ZH0', 'DZ', 'DZH'}

        self.__all_russian_letters = {'а', 'б', 'в', 'г', 'д', 'е', 'ё', 'ж', 'з', 'и', 'й', 'к', 'л', 'м', 'н', 'о',
                                      'п', 'р', 'с', 'т', 'у', 'ф', 'х', 'ц', 'ч', 'ш', 'щ', 'ъ', 'ы', 'ь', 'э', 'ю',
                                      'я'}

        self.__hard_and_soft_signs = {'ъ', 'ь'}

        self.__vocals = {'а', 'о', 'у', 'э', 'ы', 'и', 'я', 'ё', 'ю', 'е', 'а+', 'о+', 'у+', 'э+', 'ы+', 'и+', 'я+',
                         'ё+', 'ю+', 'е+'}

        self.__double_vocals = {'е', 'ё', 'ю', 'я', 'е+', 'ё+', 'ю+', 'я+'}

        # назвать получше
        self.__gen_vocals_hard = {'ъ', 'а', 'о', 'у', 'э', 'ы', 'а+', 'о+', 'у+', 'э+', 'ы+'}
        self.__gen_vocals_soft = {'ь', 'я', 'ё', 'ю', 'е', 'и', 'я+', 'ё+', 'ю+', 'е+', 'и+'}

        self.__consonants = {'б', 'в', 'г', 'д', 'ж', 'з', 'й', 'к', 'л', 'м', 'н', 'п', 'р', 'с', 'т', 'ф', 'х', 'ц',
                             'ч', 'ш', 'щ'}

        self.__deaf_consonants = {'к', 'п', 'с', 'т', 'ф', 'х', 'ц', 'ч', 'ш', 'щ'}

        self.__voiced_weak_consonants = {'в', 'й', 'л', 'м', 'н', 'р'}

        self.__voiced_strong_consonants = {'б', 'г', 'д', 'з', 'ж'}

        # парные по звонкости согласные
        self.__pair_consonants = {'б', 'в', 'г', 'д', 'ж', 'з', 'к', 'п', 'с', 'т', 'ф', 'ш'}

        # непарные по звонкости согласные
        self.__nonpair_consonants = {'й', 'м', 'н', 'р', 'л', 'ц', 'ч', 'х', 'щ'}

        self.__hardsoft_consonants = {'б', 'в', 'г', 'д', 'з', 'к', 'л', 'м', 'н', 'п', 'р', 'с', 'т', 'ф', 'х'}

        self.__hard_consonants = {'ж', 'ш', 'ц'}
        self.__soft_consonants = {'й', 'ч', 'щ'}

        self.__letters_for_rule_27 = {'н', 'т', 'с', 'д', 'з', 'л', 'м', 'п', 'б', 'в', 'ф'}

        self.__function_words_1 = {'без', 'безо', 'близ', 'в', 'во', 'вне', 'для', 'до', 'за', 'из', 'изо', 'к', 'ко',
                                   'меж', 'на', 'над', 'о', 'об', 'обо', 'от', 'ото', 'по', 'под', 'подо', 'пред',
                                   'предо', 'при', 'про', 'с', 'со', 'у', 'чрез', 'через', 'не', 'ни', 'из-за',
                                   'из-подо', 'из-под', 'а-ля', 'по-над', 'по-за'}
        self.__function_words_2 = {'бы', 'б', 'де', 'ли', 'же', '-то', '-ка', '-либо', '-нибудь', '-таки'}

        self.__exclusions_dictionary = None
        exclusions_dictionary_name = os.path.join(os.path.dirname(__file__), 'data', 'Phonetic_Exclusions.txt')
        assert os.path.isfile(exclusions_dictionary_name), \
            'File `{0}` does not exist!'.format(exclusions_dictionary_name)
        self.__exclusions_dictionary = self.load_exclusions_dictionary(exclusions_dictionary_name)
        self.__re_for_phrase_split = re.compile(r'[\s\-]+', re.U)

        self.__r4l = RulesForGraphemes()

    @property
    def russian_letters(self) -> list:
        return sorted(list(self.__all_russian_letters))

    @property
    def russian_phonemes(self) -> list:
        return sorted(list(self.__russian_phonemes_set))

    @property
    def silence_name(self) -> str:
        return self.__silence_name

    def load_exclusions_dictionary(self, file_name: str) -> dict:
        words_and_transcriptions = dict()
        with codecs.open(file_name, mode='r', encoding='utf-8', errors='ignore') as dictionary_file:
            cur_line = dictionary_file.readline()
            cur_line_index = 1
            while len(cur_line):
                error_message = "File `{0}`, line {1}: description of this word and its transcription is " \
                                "incorrect!".format(file_name, cur_line_index)
                prepared_line = cur_line.strip()
                if len(prepared_line):
                    words_of_line = prepared_line.split()
                    nwords = len(words_of_line)
                    assert nwords >= 2, error_message
                    word_name = words_of_line[0].lower()
                    assert any([c in (self.__all_russian_letters | {'-', '+'}) for c in word_name]), error_message
                    assert word_name not in words_and_transcriptions, error_message
                    word_transcription = list()
                    for cur_phoneme in words_of_line[1:]:
                        prepared_phoneme = cur_phoneme.upper()
                        # переписать исключения
                        # assert prepared_phoneme in self.__russian_phonemes_set, error_message
                        word_transcription.append(prepared_phoneme)
                    words_and_transcriptions[word_name] = copy.copy(word_transcription)
                cur_line = dictionary_file.readline()
                cur_line_index += 1
        assert len(words_and_transcriptions) > 0, \
            "File `{0}`: there are no words and their transcriptions!".format(file_name)
        return words_and_transcriptions

    def check_word(self, checked_word: str):
        assert len(checked_word) > 0, 'Checked word is empty string!'
        assert all([c in (self.__all_russian_letters | {'+', '-'}) for c in checked_word.lower()]), \
            '`{0}`: this word contains inadmissible characters!'.format(checked_word)
        assert len(list(filter(lambda c: c in self.__all_russian_letters, checked_word.lower()))) > 0, \
            '`{0}`: this word is incorrect!'.format(checked_word)

    def check_phrase(self, checked_phrase: str):
        assert len(checked_phrase) > 0, 'Checked phrase is empty string!'
        assert all([c in (self.__all_russian_letters | {' ', '+', '-'} | {'s', 'i', 'l'})
                    for c in checked_phrase.lower()]), \
            '`{0}`: this phrase contains inadmissible characters!'.format(checked_phrase)
        for cur_word in self.__re_for_phrase_split.split(checked_phrase.lower()):
            assert (len(list(filter(lambda c: c in self.__all_russian_letters, cur_word))) > 0) \
                   or (cur_word.lower() == 'sil'), '`{0}`: this phrase is incorrect!'.format(checked_phrase)

    def word_to_phonemes(self, source_word: str) -> list:
        self.check_word(source_word)
        error_message = '`{0}`: this word is incorrect!'.format(source_word)
        prepared_word = source_word.lower()
        if prepared_word in self.__exclusions_dictionary:
            return self.__exclusions_dictionary[prepared_word]
        if '+' not in prepared_word:
            counter = len(prepared_word) - len(re.sub(r'[аоуэыияёею]', '', prepared_word))
            if counter > 1:
                warnings.warn('`{0}`: the accent for this word is unknown!'.format(source_word))
        if prepared_word in self.__exclusions_dictionary:
            return self.__exclusions_dictionary[prepared_word]
        if '\'' in prepared_word:
            prepared_word = prepared_word.replace('\'', '')
        if '-' in prepared_word:
            if (not self.in_function_words_1(prepared_word)) and (not self.in_function_words_2(prepared_word)):
                word_parts = list(filter(lambda a: len(a) > 0, map(lambda b: b.strip(), prepared_word.split('-'))))
                assert len(word_parts) > 0, error_message
                prepared_word_parts = [word_parts[0]]
                for cur_part in word_parts[1:]:
                    if self.in_function_words_1('-' + cur_part) or self.in_function_words_2('-' + cur_part):
                        prepared_word_parts.append('-' + cur_part)
                    else:
                        prepared_word_parts.append(cur_part)
                return self.phrase_to_phonemes(' '.join(prepared_word_parts))
            prepared_word = self.__remove_character(prepared_word, '-')
        letters_list = self.__word_to_letters_list(self.__prepare_word(prepared_word))
        n = len(letters_list)
        assert n > 0, error_message
        ind = 0
        # начинаем формировать транскрипцию
        transcription = list()
        while ind < n:
            if letters_list[ind] in self.__hard_and_soft_signs:
                ind += 1
                continue
            old_ind = ind
            if letters_list[ind] in self.__vocals:
                new_phonemes, ind = self.__apply_rule_for_vocals_ru(letters_list, ind)
            else:
                assert letters_list[ind] in self.__consonants, error_message
                new_phonemes, ind = self.__apply_rule_for_consonants_ru(letters_list, ind)
            transcription += new_phonemes
            assert ind > old_ind, error_message
        assert len(transcription) > 0, '`{0}`: this word cannot be transcribed!'.format(source_word)
        return self.__remove_repeats_from_transcription(transcription)

    def phrase_to_phonemes(self, source_phrase: str) -> list:
        self.check_phrase(source_phrase)
        error_message = '`{0}`: this phrase is incorrect!'.format(source_phrase)
        words_in_phrase = list()
        for cur_word in source_phrase.lower().split(' '):
            if '\'' in cur_word:
                cur_word = cur_word.replace('\'', '')
            if '-' in cur_word:
                if self.in_function_words_1(cur_word) or self.in_function_words_2(cur_word) \
                        or cur_word in self.__exclusions_dictionary:
                    words_in_phrase.append(cur_word)
                else:
                    word_parts = list(filter(lambda a: len(a) > 0, map(lambda b: b.strip(), cur_word.split('-'))))
                    assert len(word_parts) > 0, error_message
                    words_in_phrase.append(word_parts[0])
                    for cur_part in word_parts[1:]:
                        if self.in_function_words_1('-' + cur_part) or self.in_function_words_2('-' + cur_part):
                            words_in_phrase.append('-' + cur_part)
                        else:
                            words_in_phrase.append(cur_part)
            else:
                words_in_phrase.append(cur_word)
        transcriptions_of_words = list()
        nphrase = len(words_in_phrase)
        for cur_word in words_in_phrase:
            if cur_word == self.__silence_name:
                transcriptions_of_words.append([self.__silence_name])
            elif cur_word in self.__exclusions_dictionary:
                transcriptions_of_words.append(self.__exclusions_dictionary[cur_word])
            else:
                transcriptions_of_words.append(self.word_to_phonemes(cur_word))
        prepared_transcriptions_of_words = list()
        prepared_words_in_phrase = list()
        ind = 0
        while ind < nphrase:
            cur_word = words_in_phrase[ind]
            assert not self.in_function_words_2(cur_word), error_message
            if cur_word == self.__silence_name:
                prepared_words_in_phrase.append(cur_word)
                prepared_transcriptions_of_words.append([self.__silence_name])
                ind += 1
            elif self.in_function_words_1(cur_word):
                assert ind < (nphrase - 1), error_message
                next_word = words_in_phrase[ind + 1]
                assert (not self.in_function_words_1(next_word)) and (not self.in_function_words_2(next_word)) \
                       and (next_word != self.__silence_name), error_message
                united_transcription = self.__unite_transcriptions_of_functional_word_and_content_word(
                    cur_word, transcriptions_of_words[ind], next_word, transcriptions_of_words[ind + 1])
                if ind < (nphrase - 2):
                    united_word = ' '.join([cur_word, next_word])
                    next_word = words_in_phrase[ind + 2]
                    if self.in_function_words_2(next_word):
                        united_transcription = self.__unite_transcriptions_of_functional_word_and_content_word(
                            united_word, united_transcription, next_word, transcriptions_of_words[ind + 2])
                        prepared_transcriptions_of_words.append(united_transcription)
                        prepared_words_in_phrase.append(' '.join([united_word, next_word]))
                        ind += 3
                    else:
                        prepared_transcriptions_of_words.append(united_transcription)
                        prepared_words_in_phrase.append(united_word)
                        ind += 2
                else:
                    prepared_transcriptions_of_words.append(united_transcription)
                    prepared_words_in_phrase.append(' '.join([cur_word, next_word]))
                    ind += 2
            else:
                if ind < (nphrase - 1):
                    next_word = words_in_phrase[ind + 1]
                    if self.in_function_words_2(next_word):
                        united_transcription = self.__unite_transcriptions_of_functional_word_and_content_word(
                            cur_word, transcriptions_of_words[ind], next_word, transcriptions_of_words[ind + 1])
                        prepared_transcriptions_of_words.append(united_transcription)
                        prepared_words_in_phrase.append(' '.join([cur_word, next_word]))
                        ind += 2
                    else:
                        prepared_transcriptions_of_words.append(transcriptions_of_words[ind])
                        prepared_words_in_phrase.append(cur_word)
                        ind += 1
                else:
                    prepared_transcriptions_of_words.append(transcriptions_of_words[ind])
                    prepared_words_in_phrase.append(cur_word)
                    ind += 1

        nphrase = len(prepared_words_in_phrase)
        assert nphrase > 0, error_message
        phrase_transcription = prepared_transcriptions_of_words[0]
        if nphrase > 1:
            cur_word = prepared_words_in_phrase[0]
            for ind in range(nphrase - 1):
                next_word = prepared_words_in_phrase[ind + 1]
                next_transcription = prepared_transcriptions_of_words[ind + 1]
                phrase_transcription = self.__unite_transcriptions_of_two_content_words(
                    cur_word, phrase_transcription, next_word, next_transcription)
                cur_word = next_word
        return phrase_transcription

    def in_function_words_1(self, source_word: str) -> bool:
        return self.__remove_character(source_word, '+').lower() in self.__function_words_1

    def in_function_words_2(self, source_word: str) -> bool:
        return self.__remove_character(source_word, '+').lower() in self.__function_words_2

    def __remove_character(self, source_word: str, removed_char: str) -> str:
        return ''.join(list(filter(lambda a: a != removed_char, source_word.lower())))

    def __prepare_word(self, cur_word: str) -> str:
        # правила 21-24
        prepared_word = cur_word.lower().strip()
        replace_pairs = [('стн', 'сн'), ('стл', 'сл'), ('нтг', 'нг'), ('здн', 'зн'), ('здц', 'зц'),
                         ('ндц', 'нц'), ('рдц', 'рц'), ('ндш', 'нш'), ('гдт', 'гт'), ('лнц', 'нц'),
                         ('сч', 'щ'), ('жч', 'щ'), ('сш', 'ш'), ('зж', 'ж'),
                         ('тс', 'ц'), ('тьс', 'ц'), ('тц', 'ц'), ('дс', 'ц'), ('дц', 'ц')]
        if len(prepared_word) > 2 and prepared_word[-2:] == 'го':
            prepared_word = prepared_word[:-2] + 'ва'
        for repl_from, repl_to in replace_pairs:
            prepared_word = prepared_word.replace(repl_from, repl_to)
        return prepared_word

    def __word_to_letters_list(self, cur_word: str) -> list:
        vocal_letters = set(filter(lambda letter: not letter.endswith('+'), self.__vocals))
        error_message = "`{0}`: this word is incorrect!".format(cur_word)
        letters_list = list()
        new_letter = ''
        for ind in range(len(cur_word)):
            if cur_word[ind] == '+':
                assert new_letter in vocal_letters, error_message
                new_letter += cur_word[ind]
            else:
                assert cur_word[ind] in self.__all_russian_letters, error_message
                if len(new_letter):
                    letters_list.append(new_letter)
                new_letter = cur_word[ind]
        if len(new_letter):
            letters_list.append(new_letter)
        del vocal_letters
        return letters_list

    def __apply_rule_for_vocals_ru(self, letters_list: list, cur_pos: int) -> tuple:
        new_phonemes_list = list()
        case = 0
        if (cur_pos == 0) or (letters_list[cur_pos - 1] in self.__vocals | self.__hard_and_soft_signs) \
                or (letters_list[cur_pos - 1] not in self.__all_russian_letters):
            # мы могли сюда прийти только после гласной или Ь, Ъ => нужно добавить J0
            if letters_list[cur_pos] in self.__double_vocals:
                new_phonemes_list.append('J0')
            if cur_pos + 1 >= len(letters_list):
                case = 1
            else:
                case = 2
        # не начало слова, слева Й, Ч, Щ
        elif letters_list[cur_pos - 1] in self.__soft_consonants:
            if cur_pos + 1 >= len(letters_list):
                case = 3
            else:
                case = 4
        # не начало слова, слева Ж, Ц, Ш
        elif letters_list[cur_pos - 1] in self.__hard_consonants:
            if cur_pos + 1 >= len(letters_list):
                case = 5
            else:
                case = 6
        # не начало слова, слева парная по твердости
        elif letters_list[cur_pos - 1] in self.__hardsoft_consonants:
            if cur_pos + 1 >= len(letters_list):
                case = 7
            else:
                case = 8
        else:
            assert 0 == 1, "Incorrect word! " + letters_list[cur_pos]
        new_phonemes_list.append(self.__r4l.vocs[letters_list[cur_pos]].forms['case' + str(case)])
        return new_phonemes_list, cur_pos + 1

    def __apply_rule_for_consonants_ru(self, letters_list: list, cur_pos: int) -> tuple:
        new_phonemes_list = list()
        n = len(letters_list)
        if cur_pos == n - 1:
            case = 'd_hard'
        else:
            # правило 27
            if cur_pos < n - 2 and letters_list[cur_pos] in {'н', 'т', 'с', 'д', 'з'} and \
                                   letters_list[cur_pos + 1] in self.__letters_for_rule_27 and \
                                   letters_list[cur_pos + 2] in self.__gen_vocals_soft:
                case = 'n_soft'
            elif letters_list[cur_pos] == 'н' and letters_list[cur_pos + 1] in {'ч', 'щ'}:
                case = 'n_soft'
            # конец правила 27
            elif cur_pos < n - 2 and letters_list[cur_pos] == 'г' and letters_list[cur_pos + 1] == 'к':
                if letters_list[cur_pos + 2] in self.__gen_vocals_soft:
                    return ['KH0'], cur_pos + 1
                elif letters_list[cur_pos + 2] in self.__gen_vocals_hard:
                    return ['KH'], cur_pos + 1
                else:
                    case = 'd_hard'
            elif letters_list[cur_pos + 1] in self.__deaf_consonants:
                case = 'd_hard'
            elif letters_list[cur_pos + 1] in self.__voiced_weak_consonants:
                case = 'n_hard'
            elif letters_list[cur_pos + 1] in self.__gen_vocals_hard:
                case = 'n_hard'
            elif letters_list[cur_pos + 1] in self.__voiced_strong_consonants:
                case = 'v_hard'
            elif letters_list[cur_pos + 1] in self.__gen_vocals_soft - {'ь'}:
                case = 'n_soft'
            elif letters_list[cur_pos + 1] == 'ь':
                if cur_pos == n - 2:
                    case = 'd_soft'
                else:
                    if letters_list[cur_pos + 2] in self.__deaf_consonants:
                        case = 'd_soft'
                    elif letters_list[cur_pos + 2] in self.__gen_vocals_hard:
                        case = 'd_soft'
                    elif letters_list[cur_pos + 2] in self.__gen_vocals_soft:
                        case = 'n_soft'
                    elif letters_list[cur_pos + 2] in self.__voiced_weak_consonants:
                        case = 'n_soft'
                    elif letters_list[cur_pos + 2] in self.__voiced_strong_consonants:
                        case = 'v_soft'
                    else:
                        assert 0 == 1, "Incorrect word! " + letters_list[cur_pos]
            else:
                assert 0 == 1, "Incorrect word! " + letters_list[cur_pos]
        new_phonemes_list.append(self.__r4l.cons[letters_list[cur_pos]].forms[case])
        return new_phonemes_list, cur_pos + 1

    def __remove_repeats_from_transcription(self, source_transcription: list) -> list:
        prepared_transcription = list()
        previous_phoneme = ''
        for current_phoneme in source_transcription:
            if re.sub(r'[0l]', '', current_phoneme) != re.sub(r'[0l]', '', previous_phoneme):
                prepared_transcription.append(current_phoneme)
            else:
                prepared_transcription[-1] = current_phoneme + 'l'
            previous_phoneme = current_phoneme
        return prepared_transcription

    def __unite_transcriptions_of_functional_word_and_content_word(self, word1: str, transcription1: list,
                                                                   word2: str, transcription2: list) -> list:
        letters_list_1 = self.__word_to_letters_list(self.__prepare_word(word1.replace('-', '')))
        letters_list_2 = self.__word_to_letters_list(self.__prepare_word(word2.replace('-', '')))
        nword1 = len(letters_list_1)
        nword2 = len(letters_list_2)
        return self.word_to_phonemes(word1 + word2)
        if letters_list_1[nword1 - 1] in self.__consonants:
            new_phonemes = None
            if nword2 == 1:
                if letters_list_1[nword1 - 1] in self.__nonpair_consonants:
                    if letters_list_1[nword1 - 1] in {'й', 'ц', 'ч', 'щ'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 3)
                    else:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 5)
                else:
                    if letters_list_2[0] in {'п', 'т', 'к', 'ф', 'с', 'ц', 'ш', 'ч', 'х', 'щ'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 8)
                    elif letters_list_2[0] in {'б', 'д', 'г', 'з', 'ж'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 11)
                    elif letters_list_2[0] in {'в', 'ъ', 'а', 'а+', 'о', 'о+', 'у', 'у+', 'э', 'э+', 'ы', 'ы+'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 12)
                    elif letters_list_2[0] in {'я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и', 'и+'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 12)
                    elif letters_list_2[0] in {'л', 'м', 'н', 'р'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 20)
            else:
                if letters_list_1[nword1 - 1] in self.__nonpair_consonants:
                    if letters_list_1[nword1 - 1] in {'й', 'ц', 'ч', 'щ'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 3)
                    else:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 5)
                else:
                    if (letters_list_1[nword1 - 1] == 'г') and (letters_list_2[0] == 'к') \
                            and (letters_list_2[1] in {'ъ', 'а', 'а+', 'о', 'о+', 'у', 'у+', 'э', 'э+', 'ы', 'ы+'}):
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 9)
                    elif (letters_list_1[nword1 - 1] == 'г') and (letters_list_2[0] == 'к') \
                            and (letters_list_2[1] in {'я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и', 'и+'}):
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 9)
                    elif letters_list_2[0] in {'п', 'т', 'к', 'ф', 'с', 'ц', 'ш', 'ч', 'х', 'щ'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 8)
                    elif letters_list_2[0] in {'б', 'д', 'г', 'з', 'ж'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 11)
                    elif letters_list_2[0] in {'в', 'ъ', 'а', 'а+', 'о', 'о+', 'у', 'у+', 'э', 'э+', 'ы', 'ы+'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 12)
                    elif letters_list_2[0] in {'я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и', 'и+'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 12)
                    elif letters_list_2[0] in {'л', 'м', 'н', 'р'}:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 20)
            if new_phonemes is not None:
                transcription1 = transcription1[0:(len(transcription1) - 1)] + new_phonemes
        if letters_list_2[0] in self.__vocals:
            new_phonemes = None
            if letters_list_1[nword1 - 1] in ({'ь', 'ъ'} | self.__vocals):
                if (letters_list_1[nword1 - 1] == 'ь') and (letters_list_2[0] in ['о', 'о+', 'и', 'и+']):
                    if letters_list_2[0] == 'о':
                        new_phonemes = ['A']
                    elif letters_list_2[0] == 'о+':
                        new_phonemes = ['O0']
                    elif letters_list_2[0] == 'и':
                        new_phonemes = ['I']
                    else:
                        new_phonemes = ['I0']
                else:
                    new_phonemes, ind = self.__apply_rule_for_vocals_ru(letters_list_1 + letters_list_2, nword1)
            else:
                if (letters_list_2[0] in ['и', 'и+']) and (letters_list_1[nword1 - 1] in (self.__consonants - {'й'})):
                    if letters_list_2[0] == 'и':
                        new_phonemes = ['Y']
                    else:
                        new_phonemes = ['Y0']
            if not new_phonemes is None:
                if transcription2[0] == 'J':
                    transcription2 = new_phonemes + transcription2[2:]
                else:
                    transcription2 = new_phonemes + transcription2[1:]
        return self.__remove_repeats_from_transcription(transcription1 + transcription2)

    def __unite_transcriptions_of_two_content_words(self, word1: str, transcription1: list,
                                                    word2: str, transcription2: list) -> list:
        if (word1 == self.__silence_name) or (word2 == self.__silence_name):
            return self.__remove_repeats_from_transcription(transcription1 + transcription2)
        return self.word_to_phonemes(word1 + word2)
        letters_list_1 = self.__word_to_letters_list(self.__prepare_word(word1.replace('-', '').replace(' ', '')))
        letters_list_2 = self.__word_to_letters_list(self.__prepare_word(word2.replace('-', '').replace(' ', '')))
        nword1 = len(letters_list_1)
        nword2 = len(letters_list_2)
        if (letters_list_1[-1] in ['я', 'а', 'е']) and (letters_list_1[-1] == 'я' or (
                len(letters_list_1) > 1 and letters_list_1[-2] in ['ч', 'щ'])):
            letters_list_1[-1] = 'и'
        if (letters_list_1[nword1 - 1] in self.__consonants) or (letters_list_1[nword1 - 1] == 'ь'):
            new_phonemes = None
            ind = None
            if nword1 == 1:
                if (letters_list_1[nword1 - 1] in ['п', 'т', 'к', 'ф', 'с', 'ш', 'щ', 'ц', 'ч']) \
                        and (letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж']):
                    if letters_list_1[nword1 - 1] == 'щ':
                        new_phonemes = ['ZH0']
                    elif letters_list_1[nword1 - 1] == 'ц':
                        new_phonemes = ['DZ']
                    elif letters_list_1[nword1 - 1] == 'ч':
                        new_phonemes = ['DZH']
                    else:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 11)
                elif letters_list_1[nword1 - 1] in ['б', 'в', 'д', 'г', 'з', 'ж']:
                    if letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж']:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 11)
                    else:
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 8)
                elif (not letters_list_1[nword1 - 1] in self.__nonpair_consonants) \
                        and (letters_list_2[0] in ['я', 'ё', 'ю', 'е', 'и', 'я+', 'ё+', 'ю+', 'е+', 'и+']):
                    new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                         nword1 - 1, 12)
                else:
                    if nword2 > 1:
                        if letters_list_1[nword1 - 1] in self.__nonpair_consonants:
                            if (letters_list_1[nword1 - 1] == 'н') and (letters_list_2[0] in ['н', 'д', 'т', 'с']) \
                                    and (letters_list_2[1] in ['ь', 'я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и',
                                                               'и+']):
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 6)
                            elif (letters_list_1[nword1 - 1] in ['м', 'н', 'р', 'л', 'х']) \
                                    and (
                                    not letters_list_2[0] in ['я', 'ё', 'ю', 'е', 'и', 'я+', 'ё+', 'ю+', 'е+', 'и+']):
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 5)
                        else:
                            if (letters_list_1[nword1 - 1] == 'г') and (letters_list_2[0] == 'к') \
                                    and (letters_list_2[1] in ['ъ', 'а', 'а+', 'о', 'о+', 'у', 'у+', 'э', 'э+', 'ы',
                                                               'ы+']):
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 9)
                            elif (letters_list_1[nword1 - 1] == 'г') and (letters_list_2[0] == 'к') \
                                    and (letters_list_2[1] in ['я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и', 'и+']):
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 9)
                            elif letters_list_2[0] in ['п', 'т', 'к', 'ф', 'с', 'ц', 'ш', 'ч', 'х', 'щ']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 8)
                            elif letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 11)
                            elif letters_list_2[0] in ['в', 'ъ', 'а', 'а+', 'о', 'о+', 'у', 'у+', 'э', 'э+', 'ы', 'ы+']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 12)
                            elif letters_list_2[0] in ['я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и', 'и+']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 13)
                            elif letters_list_2[0] in ['л', 'м', 'н', 'р']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 20)
                    else:
                        if letters_list_1[nword1 - 1] in self.__nonpair_consonants:
                            if (letters_list_1[nword1 - 1] in ['м', 'н', 'р', 'л', 'х']) \
                                    and (
                                    not letters_list_2[0] in ['я', 'ё', 'ю', 'е', 'и', 'я+', 'ё+', 'ю+', 'е+', 'и+']):
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 5)
                        else:
                            if letters_list_2[0] in ['п', 'т', 'к', 'ф', 'с', 'ц', 'ш', 'ч', 'х', 'щ']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 8)
                            elif letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 11)
                            elif letters_list_2[0] in ['в', 'ъ', 'а', 'а+', 'о', 'о+', 'у', 'у+', 'э', 'э+', 'ы', 'ы+']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 12)
                            elif letters_list_2[0] in ['я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и', 'и+']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 13)
                            elif letters_list_2[0] in ['л', 'м', 'н', 'р']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 1, 20)
            else:
                if letters_list_1[nword1 - 1] == 'ь':
                    if (letters_list_1[nword1 - 2] in ['п', 'т', 'к', 'ф', 'с', 'ш', 'щ', 'ц', 'ч']) \
                            and (letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж']):
                        if letters_list_1[nword1 - 2] == 'щ':
                            new_phonemes = ['ZH0']
                        elif letters_list_1[nword1 - 2] == 'ц':
                            new_phonemes = ['DZ']
                        elif letters_list_1[nword1 - 2] == 'ч':
                            new_phonemes = ['DZH']
                        else:
                            new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                 nword1 - 2, 11)
                    elif letters_list_1[nword1 - 2] in ['б', 'в', 'д', 'г', 'з', 'ж']:
                        if letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж', 'я', 'ё', 'ю', 'е', 'и', 'я+', 'ё+', 'ю+',
                                                 'е+', 'и+']:
                            new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                 nword1 - 2, 15)
                        else:
                            new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                 nword1 - 2, 14)
                    else:
                        if not letters_list_1[nword1 - 2] in self.__nonpair_consonants:
                            if letters_list_2[0] in ['п', 'т', 'к', 'ф', 'с', 'ш', 'ц', 'ч', 'х', 'щ']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 2, 14)
                            elif letters_list_2[0] in ['я', 'ё', 'ю', 'е', 'и', 'я+', 'ё+', 'ю+', 'е+', 'и+']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 2, 15)
                            elif letters_list_2[0] in ['й', 'м', 'н', 'р', 'л']:
                                new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                     nword1 - 2, 17)
                else:
                    if (letters_list_1[nword1 - 1] in ['п', 'т', 'к', 'ф', 'с', 'ш', 'щ', 'ц', 'ч']) \
                            and (letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж']):
                        if letters_list_1[nword1 - 1] == 'щ':
                            new_phonemes = ['ZH0']
                        elif letters_list_1[nword1 - 1] == 'ц':
                            new_phonemes = ['DZ']
                        elif letters_list_1[nword1 - 1] == 'ч':
                            new_phonemes = ['DZH']
                        else:
                            new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                 nword1 - 1, 11)
                    elif letters_list_1[nword1 - 1] in ['б', 'д', 'г', 'з', 'ж']:
                        if letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж']:
                            new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                 nword1 - 1, 11)
                        else:
                            new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                                 nword1 - 1, 8)
                    elif (not letters_list_1[nword1 - 1] in self.__nonpair_consonants) and (
                        letters_list_2[0] in ['я', 'ё', 'ю', 'е', 'и', 'я+', 'ё+', 'ю+', 'е+', 'и+']):
                        new_phonemes, ind = self.__apply_rule_for_one_letter(letters_list_1 + letters_list_2,
                                                                             nword1 - 1, 12)
                    else:
                        if nword2 > 1:
                            if letters_list_1[nword1 - 1] in self.__nonpair_consonants:
                                if (letters_list_1[nword1 - 1] == 'н') and (letters_list_2[0] in ['н', 'д', 'т', 'с']) \
                                        and (letters_list_2[1] in ['ь', 'я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и',
                                                                   'и+']):
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 6)
                                elif (letters_list_1[nword1 - 1] in ['м', 'н', 'р', 'л', 'х']) \
                                        and (not letters_list_2[0] in ['я', 'ё', 'ю', 'е', 'и', 'я+', 'ё+', 'ю+', 'е+',
                                                                       'и+']):
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 5)
                            else:
                                if (letters_list_1[nword1 - 1] == 'г') and (letters_list_2[0] == 'к') \
                                        and (letters_list_2[1] in ['ъ', 'а', 'а+', 'о', 'о+', 'у', 'у+', 'э', 'э+', 'ы',
                                                                   'ы+']):
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 9)
                                elif (letters_list_1[nword1 - 1] == 'г') and (letters_list_2[0] == 'к') \
                                        and (letters_list_2[1] in ['я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и',
                                                                   'и+']):
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 9)
                                elif letters_list_2[0] in ['п', 'т', 'к', 'ф', 'с', 'ц', 'ш', 'ч', 'х', 'щ']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 8)
                                elif letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 11)
                                elif letters_list_2[0] in ['в', 'ъ', 'а', 'а+', 'о', 'о+', 'у', 'у+', 'э', 'э+', 'ы',
                                                           'ы+']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 12)
                                elif letters_list_2[0] in ['я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и', 'и+']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 13)
                                elif letters_list_2[0] in ['л', 'м', 'н', 'р']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 20)
                        else:
                            if letters_list_1[nword1 - 1] in self.__nonpair_consonants:
                                if (letters_list_1[nword1 - 1] in ['м', 'н', 'р', 'л', 'х']) \
                                        and (not letters_list_2[0] in ['я', 'ё', 'ю', 'е', 'и', 'я+', 'ё+', 'ю+', 'е+',
                                                                       'и+']):
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 5)
                            else:
                                if letters_list_2[0] in ['п', 'т', 'к', 'ф', 'с', 'ц', 'ш', 'ч', 'х', 'щ']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 8)
                                elif letters_list_2[0] in ['б', 'д', 'г', 'з', 'ж']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 11)
                                elif letters_list_2[0] in ['в', 'ъ', 'а', 'а+', 'о', 'о+', 'у', 'у+', 'э', 'э+', 'ы',
                                                           'ы+']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 12)
                                elif letters_list_2[0] in ['я', 'я+', 'ё', 'ё+', 'ю', 'ю+', 'е', 'е+', 'и', 'и+']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 13)
                                elif letters_list_2[0] in ['л', 'м', 'н', 'р']:
                                    new_phonemes, ind = self.__apply_rule_for_one_letter(
                                        letters_list_1 + letters_list_2, nword1 - 1, 20)
            if not new_phonemes is None:
                transcription1 = transcription1[0:(len(transcription1) - 1)] + new_phonemes
        if letters_list_2[0] in self.__vocals:
            new_phonemes = None
            if letters_list_1[nword1 - 1] in ({'ь', 'ъ'} | self.__vocals):
                if (letters_list_1[nword1 - 1] == 'ь') and (letters_list_2[0] in ['о', 'о+', 'и', 'и+']):
                    if letters_list_2[0] == 'о':
                        new_phonemes = ['A']
                    elif letters_list_2[0] == 'о+':
                        new_phonemes = ['O0']
                    elif letters_list_2[0] == 'и':
                        new_phonemes = ['I']
                    else:
                        new_phonemes = ['I0']
                else:
                    new_phonemes, ind = self.__apply_rule_for_vocals_ru(letters_list_1 + letters_list_2, nword1)
            else:
                if (letters_list_2[0] in ['и', 'и+']) and (letters_list_1[nword1 - 1] in (self.__consonants - {'й'})):
                    if letters_list_2[0] == 'и':
                        new_phonemes = ['Y']
                    else:
                        new_phonemes = ['Y0']
            if not new_phonemes is None:
                if transcription2[0] == 'J':
                    transcription2 = new_phonemes + transcription2[2:]
                else:
                    transcription2 = new_phonemes + transcription2[1:]
        return self.__remove_repeats_from_transcription(transcription1 + transcription2)


g = Grapheme2Phoneme()
print(g.word_to_phonemes('матчбо+л'))