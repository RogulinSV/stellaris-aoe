#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from string import Template

from domains import Tradition, Category as TraditionCategory, Module


class GatheringTraditionsDataTemplate(object):
    def __init__(self):
        self.__categories = list()
        self.__compiled = dict()
        self.__templates = dict()

        self.__templates['prefix'] = Template('''
    # Module $module: $count traditions discovered\
''')
        self.__templates['init'] = Template('''\
    set_variable = {
        which = "espionage_data_tradition_count"
        value = 0
    }
    set_variable = {
        which = "espionage_data_tradition_count_adopted"
        value = 0
    }
    set_variable = {
        which = "espionage_data_tradition_count_finished"
        value = 0
    }
''')
        self.__templates['dropper'] = Template('''\
    set_variable = {
        which = "espionage_data_tradition_count_${category}"
        value = 0
    }
''')
        self.__templates['setter1'] = Template('''\
        if = {
            limit = {
                check_variable = {
                    which = "espionage_data_tradition_count_${category}"
                    value = ${initial}
                }
            }
            set_variable = {
                which = "espionage_data_tradition_count_${category}"
                value = ${percent}
            }
        }
        else = {
            change_variable = {
                which = "espionage_data_tradition_count_${category}"
                value = ${percent}
            }
        }
        change_variable = {
            which = "espionage_data_tradition_count"
            value = 1
        }\
''')
        self.__templates['setter2'] = Template('''\
        change_variable = {
            which = "espionage_data_tradition_count_${category}"
            value = ${percent}
        }
        change_variable = {
            which = "espionage_data_tradition_count"
            value = 1
        }
        change_variable = {
            which = "espionage_data_tradition_count_adopted"
            value = 1
        }\
''')
        self.__templates['setter3'] = Template('''\
        change_variable = {
            which = "espionage_data_tradition_count_finished"
            value = 1
        }\
''')
        self.__templates['limiter'] = Template('''
    if = {
        limit = {
            has_tradition = "${tradition}"
        }
        $setter
    }\
''')
        self.__templates['suffix'] = Template('''
    # Cleanup\
''')
        self.__templates['cleanup'] = Template('''
    if = {
        limit = {
            check_variable = {
                which = "espionage_data_tradition_count_${category}"
                value > 100
            }
        }
        set_variable = {
            which = "espionage_data_tradition_count_${category}"
            value = 100
        }
    }\
''')

    def process(self, category: TraditionCategory, module: Module):
        if category.category in self.__categories:
            logging.info('... traditions category %s from module %s skipped' % (category, module))
            return

        self.__categories.append(category.category)
        module = str(module)
        if module not in self.__compiled:
            self.__compiled[module] = list()

        initial_percent = 5
        traditions = [tradition for tradition in category.traditions]
        remove = list()
        for tradition in traditions:
            tradition = category.traditions.get(tradition)  # type: Tradition

            if tradition.is_finished:
                setter = self.__templates['setter3'].substitute(
                    percent=0
                )
                self.__compiled[module].append(
                    self.__templates['limiter'].substitute(
                        tradition=tradition.name,
                        setter=setter.lstrip()
                    )
                )
                remove.append(tradition.name)
            elif tradition.is_adopted:
                setter = self.__templates['setter2'].substitute(
                    category=category.category,
                    percent=initial_percent
                )
                self.__compiled[module].append(
                    self.__templates['limiter'].substitute(
                        tradition=tradition.name,
                        setter=setter.lstrip()
                    )
                )
                remove.append(tradition.name)

        traditions = [tradition for tradition in sorted(traditions) if tradition not in remove]
        percent = round(100 / len(traditions))
        total_percent = 0
        for i, tradition in enumerate(traditions):
            tradition = category.traditions.get(tradition)  # type: Tradition

            if i == len(traditions) - 1:
                percent = 100 - total_percent
            total_percent = total_percent + percent

            setter=self.__templates['setter1'].substitute(
                category=category.category,
                percent=percent,
                initial=initial_percent
            )
            self.__compiled[module].append(
                self.__templates['limiter'].substitute(
                    tradition=tradition.name,
                    setter=setter.lstrip()
                )
            )

    def compile(self) -> list:
        compiled = list()

        compiled.append('intelligence_gather_traditions_data = {\n')
        compiled.append(self.__templates['init'].substitute(none=None))
        for category in self.__categories:
            compiled.append(self.__templates['dropper'].substitute(category=category))
        for module in self.__compiled:
            compiled.append(self.__templates['prefix'].substitute(module=module, count=len(self.__compiled.get(module))))
            compiled.extend(self.__compiled.get(module))
        # compiled.append(self.__templates['suffix'].substitute(none=None))
        # for category in self.__categories:
        #     compiled.append(self.__templates['cleanup'].substitute(category=category))
        compiled.append('\n}')

        return compiled

    @staticmethod
    def supports(value):
        return isinstance(value, TraditionCategory)

    def name(self) -> str:
        return 'gathering_traditions_data_template.txt'
