#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from string import Template
from domains import Module, Technology


class GatheringTechnologyDataTemplate(object):
    def __init__(self):
        self.__technologies = list()
        self.__areas = set()
        self.__categories = set()
        self.__templates = dict()
        self.__compiled = dict()

        self.__templates['dropper'] = Template('''\
    set_variable = {
        which = "espionage_data_technology_count_$tag"
        value = 0
    }
''')
        self.__templates['prefix'] = Template('''\
    # Module $module: $count technologies discovered
''')
        self.__templates['limiter'] = Template('''\
    if = {
        limit = {
            has_technology = "$name"
        }
        $modifiers
    }
''')
        self.__templates['modifier'] = Template('''\
        change_variable = {
            which = "espionage_data_technology_count_$tag"
            value = 1
        }\
''')

    def process(self, technology: Technology, module: Module):
        if technology.name in self.__technologies:
            logging.info('... technology %s from module %s skipped' % (technology, module))
            return

        self.__technologies.append(technology.name)
        self.__areas.add(technology.area)
        for category in technology.categories:
            self.__categories.add(category)

        modifiers = list()
        modifiers.append(self.__templates['modifier'].substitute(tag='area_' + technology.area))
        if technology.is_dangerous:
            modifiers.append(self.__templates['modifier'].substitute(tag='type_dangerous'))
        elif technology.is_rare:
            modifiers.append(self.__templates['modifier'].substitute(tag='type_rare'))
        for category in technology.categories:
            modifiers.append(self.__templates['modifier'].substitute(tag='category_' + category))
        if len(modifiers) > 0:
            module = str(module)
            if module not in self.__compiled:
                self.__compiled[module] = list()
            self.__compiled[module].append(
                self.__templates['limiter'].substitute(name=technology.name, modifiers="\n".join(modifiers).lstrip())
            )

    def compile(self) -> list:
        compiled = list()

        compiled.append('intelligence_gather_technology_data = {\n')
        for area in sorted(self.__areas):
            compiled.append(self.__templates['dropper'].substitute(tag='area_' + area))
        for category in sorted(self.__categories):
            compiled.append(self.__templates['dropper'].substitute(tag='category_' + category))
        for type in ('rare', 'dangerous'):
            compiled.append(self.__templates['dropper'].substitute(tag='type_' + type))

        for module in self.__compiled:
            compiled.append(self.__templates['prefix'].substitute(module=module, count=len(self.__compiled.get(module))))
            compiled.extend(self.__compiled.get(module))
        compiled.append('}')

        return compiled

    @staticmethod
    def supports(value):
        return isinstance(value, Technology)

    def name(self) -> str:
        return 'gathering_technology_data_template.txt'
