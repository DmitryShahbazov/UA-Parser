import csv
import operator
import os
import re

from flask_script import Command, Option
from user_agents import parse


class UaParser(Command):
    """
    Утилита для парсинга лога с юзер агентами
    Пример строки: Count "UserAgent"
    """

    def __init__(self):
        super().__init__()
        self.top = 100  # По умолчанию ставим топ-100
        self.path = '/spool1/'  # Путь для сохранения отчета по умолчанию в папку с логами

    def get_options(self):
        return (
            Option('-l', '--logfile', dest='logfile', type=str, help='Path to log'),
            Option('-t', '--top', dest='top', type=int, help='How much browsers will be in top'),
            Option('-p', '--path', dest='path', type=str, help='Path to save results'),
        )

    def run(self, logfile: str, top: int, path: str):
        if not logfile:
            print("Required -l parameter\n")
            exit(1)

        if top:
            self.top = top

        if path:
            self.path = path

        print('Script started!')
        self.get_parsed_ua(self.parse_log(logfile))
        print('Done!')

    @staticmethod
    def parse_log(logfile: str) -> dict:
        """
        Парсим файл со статистикой по юзер агентам
        Ищем строки по регэксп паттерну, далее собираем в словарь - browser + version: count
        """
        ua_dict = {}
        print('Parsing now...')
        regex = re.compile(r'^\s*(\d+)\s+"(.+)"')
        with open(logfile) as fh:
            for line in fh:

                regex_matches = re.search(regex, line)

                if regex_matches:
                    ua_count = regex_matches.group(1)
                    ua = parse(regex_matches.group(2))
                    parsed_ua = f'{ua.browser.family} {ua.browser.version_string}'
                    # Если у нас еще не было такого ключа(браузер + версия), то 0 + количество
                    # Если у нас уже есть такой ключ, то старое количество + новое
                    ua_dict[parsed_ua] = ua_dict.get(parsed_ua, 0) + int(ua_count)

        print('Parsing done!')

        return ua_dict

    @staticmethod
    def get_all_browser_count(ua_dict: dict) -> int:
        """
        Считаем общее количество Юзер Агентов
        """
        all_count = 0
        for _, value in ua_dict.items():
            all_count += value

        return all_count

    @staticmethod
    def get_percent(all_count: int, value: int) -> float:
        """
        Берем процент от общего числа
        """
        return (value / all_count) * 100

    def get_parsed_ua(self, ua_dict: dict):
        i = 0
        all_percents = 0
        others_dict = {}
        all_browsers_count = self.get_all_browser_count(ua_dict)  # Вычисляем общее количество ua
        regex = re.compile(r'(.+) (\d+)\.(\d+)')

        print('Writing in file now...')

        with open(os.path.join(self.path, 'ua_output.tsv'), 'w', newline='') as f_output:
            tsv_writer = csv.writer(f_output, delimiter='\t')
            tsv_writer.writerow(['#', 'Percent  ', 'Count', 'Browser', 'Major version', 'Minor version'])

            for key, value in sorted(ua_dict.items(), key=operator.itemgetter(1), reverse=True):
                i += 1
                percent = self.get_percent(all_browsers_count, value)
                all_percents += percent

                # Расчленям строку на браузер мажорная версия и минорная.
                regex_matches = re.search(regex, key)

                if regex_matches:
                    browser = regex_matches.group(1)
                    browser_major = regex_matches.group(2)
                    browser_minor = regex_matches.group(3)
                else:
                    browser = key
                    browser_major = 0
                    browser_minor = 0

                # Ставим ограничение для ТОП 100
                if i > self.top:
                    # Общий процент по остальным браузерам
                    others_dict['percent'] = others_dict.get('percent', 0) + percent
                    # Общее количество по остальным браузерам
                    others_dict['count'] = others_dict.get('count', 0) + value
                else:
                    tsv_writer.writerow([i, f'{percent:2f}', value, browser, browser_major, browser_minor])

            # Пишем остальные браузеры, которые не вошли в ТОП
            if others_dict:
                # Пишем данные по всем остальным браузерам
                tsv_writer.writerow(['#####', f'{others_dict["percent"]:2f}', others_dict['count'], 'Others', 0, 0])

            # Пишем общую статистику
            tsv_writer.writerow(['#####', f'{all_percents:2f}', all_browsers_count, '#####', '#####', '#####'])
