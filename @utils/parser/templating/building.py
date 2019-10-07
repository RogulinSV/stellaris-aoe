#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from string import Template
from domains import Building, Module


class DemolishBuildingRulesTemplate(object):
    def __init__(self):
        self.__buildings = list()
        self.__compiled = dict()
        self.__templates = dict()

        self.__templates['prefix'] = Template('''\
        # Module $module: $count buildings discovered
''')
        self.__templates['rank1'] = Template('''\
            modifier = {
                factor = 0
                event_target:espionage_origin_spy = {
                    is_intelligencer_not_ranked = yes
                }
            }\
''')
        self.__templates['rank2'] = Template('''\
            modifier = {
                factor = 0
                event_target:espionage_origin_spy = {
                    NOR = {
                        is_intelligencer_has_rank_2 = yes
                        is_intelligencer_has_rank_3 = yes
                        is_intelligencer_has_rank_4 = yes
                        is_intelligencer_has_rank_5 = yes
                    }
                }
            }\
''')
        self.__templates['rank3'] = Template('''\
            modifier = {
                factor = 0
                event_target:espionage_origin_spy = {
                    NOR = {
                        is_intelligencer_has_rank_3 = yes
                        is_intelligencer_has_rank_4 = yes
                        is_intelligencer_has_rank_5 = yes
                    }
                }
            }\
''')
        self.__templates['rank4'] = Template('''\
            modifier = {
                factor = 0
                event_target:espionage_origin_spy = {
                    NOR = {
                        is_intelligencer_has_rank_4 = yes
                        is_intelligencer_has_rank_5 = yes
                    }
                }
            }\
''')
        self.__templates['rank5'] = Template('''\
            modifier = {
                factor = 0
                event_target:espionage_origin_spy = {
                    NOT = {
                        is_intelligencer_has_rank_5 = yes
                    }
                }
            }\
''')
        self.__templates['rule'] = Template('''\
        # Demolish $description
        5 = {
            $rank
            modifier = {
                factor = 0
                event_target:espionage_target_planet = {
                    NOT = {
                        has_building = "$building"
                    }
                }
            }
            event_target:espionage_target_planet = {
                remove_building = "$building"
                add_building = "building_debris"
            }
            event_target:espionage_target_country = {
                create_message = {
                    type = MESSAGE_SPY_ENCOUNTERED_PLANETARY_DIVERSION
                    localization = MESSAGE_SPY_DEMOLISH_${localization}_LOCALISATION
                    days = 30
                    target = this
                    variable = { type = name localization = TARGET_PLANET scope = event_target:espionage_target_planet }
                }
            }
            event_target:espionage_origin_country = {
                create_message = {
                    type = MESSAGE_SPY_ORGANIZED_PLANETARY_DIVERSION
                    localization = MESSAGE_SPY_ORGANIZED_DIVERSION_ON_${localization}_LOCALISATION
                    days = 30
                    target = this
                    variable = { type = name localization = ORIGIN_PLANET scope = event_target:espionage_origin_planet }
                    variable = { type = name localization = TARGET_COUNTRY scope = event_target:espionage_target_country }
                    variable = { type = name localization = TARGET_PLANET scope = event_target:espionage_target_planet }
                }
            }
            log = ">>> try_commit_sabotage effect: $description was demolished"
        }
''')

    def process(self, building: Building, module: Module):
        if building.name in self.__buildings:
            logging.info('... building %s from module %s skipped' % (building, module))
            return

        self.__buildings.append(building.name)
        module = str(module)
        if module not in self.__compiled:
            self.__compiled[module] = list()

        categories = {
            'amenity': 1,
            'army': 5,
            'government': 5,
            'manufacturing': 4,
            'pop_assembly': 2,
            'research': 2,
            'resource': 2,
            'trade': 3,
            'unity': 1
        }
        upgrades = building.upgrade
        if len(upgrades) > 0:
            if building.category in categories and categories.get(building.category) is not None:
                rank = round(min(len(upgrades[0]), 5) * 0.5 + min(building.buildtime / 180, 5) * 0.2 + categories.get(building.category) * 0.3)
            else:
                rank = round(min(len(upgrades[0]), 5) * 0.5 + min(building.buildtime / 180, 5) * 0.5)
        else:
            if building.category in categories and categories.get(building.category) is not None:
                rank = round(min(building.buildtime / 180, 5) * 0.5 + categories.get(building.category) * 0.5)
            else:
                rank = round(min(building.buildtime / 180, 5))

        if rank > 0:
            rank = self.__templates['rank' + str(rank)].substitute(rank=rank)
        else:
            rank = '# Not ranked'
        self.__compiled[module].append(
            self.__templates['rule'].substitute(
                rank=rank.lstrip(),
                building=building.name,
                description=building.description,
                localization=building.localization
            )
        )

    def compile(self) -> list:
        compiled = list()

        for module in self.__compiled:
            compiled.append(self.__templates['prefix'].substitute(module=module, count=len(self.__compiled.get(module))))
            compiled.extend(self.__compiled.get(module))

        return compiled

    @staticmethod
    def supports(value):
        return isinstance(value, Building)

    def name(self) -> str:
        return 'demolish_building_rules_template.txt'
