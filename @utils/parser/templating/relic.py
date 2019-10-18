#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from string import Template
from domains import Relic, Module


class GatheringRelicsDataTemplate(object):
    def __init__(self):
        self.__relics = list()
        self.__compiled = dict()
        self.__templates = dict()

        self.__templates['prefix'] = Template('''
    # Module ${module}: ${count} relics discovered
''')
        self.__templates['init'] = Template('''
    set_variable = {
        which = "espionage_data_relics_count"
        value = 0
    }
    set_variable = {
        which = "espionage_data_relics_score"
        value = 0
    }
''')
        self.__templates['setter'] = Template('''\
    if = {
        limit = {
            has_relic = "${relic_name}"
        }
        change_variable = {
            which = "espionage_data_relics_count"
            value = 1
        }
        change_variable = {
            which = "espionage_data_relics_score"
            value = ${relic_score}
        }
    }
''')

    def process(self, relic: Relic, module: Module):
        if relic.name in self.__relics:
            logging.info('... relic %s from module %s skipped' % (relic, module))
            return

        self.__relics.append(relic.name)
        module = str(module)
        if module not in self.__compiled:
            self.__compiled[module] = list()
        self.__compiled[module].append(
            self.__templates['setter'].substitute(
                relic_name=relic.name,
                relic_score=relic.score
            )
        )

    def compile(self) -> list:
        compiled = list()

        compiled.append('intelligence_gather_relics_data = {')
        compiled.append(self.__templates['init'].substitute(none=None))
        for module in self.__compiled:
            compiled.append(
                self.__templates['prefix'].substitute(
                    module=module,
                    count=len(self.__compiled.get(module))
                )
            )
            compiled.extend(self.__compiled.get(module))
        compiled.append('}')

        return compiled

    @staticmethod
    def supports(value):
        return isinstance(value, Relic)

    def name(self) -> str:
        return 'gathering_relics_data_template.txt'
