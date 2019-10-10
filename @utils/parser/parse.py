#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import argparse
import logging
from pprint import pprint
from pyparsing import ParseException

from parsing import parse_string, parse_settings, BlockToken, EnumerationToken, PropertyToken
from domains import Building, Buildings, Technology, Technologies, Ship, Ships, \
    Category as TraditionCategory, Categories as TraditionCategories, Module, Settings, detect_module
from templating import GatheringTechnologyDataTemplate, GatheringTraditionsDataTemplate, DemolishBuildingRulesTemplate
from caching import Cache
from zipfile import ZipFile
from zipfile import ZipInfo

parser = argparse.ArgumentParser(description='Parse and extract data from Stellaris modules')
parser.add_argument('locations', type=str, help='Path to directory with module data', nargs='*', default=[os.getcwd()])
parser.add_argument('-s', '--settings', type=str, help='Path to file with game settings')
parser.add_argument('-l', '--log', type=str, help='Logging level')
arguments = parser.parse_args()

level = logging.DEBUG
if arguments.log is not None and hasattr(logging, arguments.log.upper()):
    level = getattr(logging, arguments.log.upper())
logging.basicConfig(format='%(asctime)s: [%(levelname)s] %(message)s', level=level)

dirs_list = list()
for i, dir_path in enumerate(arguments.locations):
    if not os.path.isabs(dir_path):
        dir_path = os.path.realpath(dir_path)
    if not os.path.exists(dir_path):
        logging.error('Unable to find location "%s"' % dir_path)
        exit(1)
    if not os.path.isdir(dir_path):
        logging.error('The indicated location "%s" is not an directory' % dir_path)
        exit(1)
    dirs_list.append(dir_path)

if len(dirs_list) == 0:
    logging.error('No directories specified for data extraction')
    exit(1)

user_settings = None
if arguments.settings is not None:
    user_settings = arguments.settings + os.sep + 'settings.txt'
    if not os.path.isabs(user_settings):
        user_settings = os.path.realpath(user_settings)
    if not os.path.exists(user_settings):
        logging.error('Unable to find location "%s" with user settings' % user_settings)
        exit(1)
    if not os.path.isfile(user_settings):
        logging.error('The indicated location "%s" with user settings is not an file' % user_settings)
        exit(1)


def parse_technology(tokens, processor: callable):
    for token in tokens:  # type: BlockToken
        if not isinstance(token, BlockToken):
            continue
        if 'area' not in token.properties or 'category' not in token.properties:
            continue

        technology = Technology.from_token(token)
        if 'cost_per_level' in token.properties:
            logging.debug('* ignored repeatable technology: ' + technology.name)
            continue
        if processor(technology):
            logging.debug('* discovered technology: ' + technology.name)
        else:
            logging.debug('* ignored technology: ' + technology.name)


def parse_building(tokens, processor: callable):
    for token in tokens:  # type: BlockToken
        if not isinstance(token, BlockToken):
            continue
        if not token.name.startswith('building_'):
            if 'can_build' not in token.properties and 'can_demolish' not in token.properties \
                    and 'base_cap_amount' not in token.properties \
                    and 'destroy_trigger' not in token.includes:
                continue

        building = Building.from_token(token)
        if 'capital' in token.properties and token.properties.get('capital') == 'yes':
            logging.debug('* ignored capital building: ' + building.name)
            continue
        if 'potential' in token.includes:
            potential = token.includes.get('potential')  # type: BlockToken
            if 'owner' in potential.includes:
                owner = potential.includes.get('owner')  # type: BlockToken
                if 'is_country_type' in owner.properties and owner.properties.get('is_country_type') == 'primitive':
                    logging.warning('* ignored primitive building: ' + building.name)
                    continue
                if 'is_primitive' in owner.properties and owner.properties.get('is_primitive') == 'yes':
                    logging.warning('* ignored primitive building: ' + building.name)
                    continue
        if processor(building):
            logging.debug('* discovered building: ' + building.name)
        else:
            logging.debug('* ignored building: ' + building.name)


def parse_ship(tokens, processor: callable):
    for token in tokens:  # type: BlockToken
        if not isinstance(token, BlockToken):
            continue
        if 'fleet_slot_size' not in token.properties:
            continue

        ship = Ship.from_token(token)
        if 'class' not in token.properties or token.properties.get('class') != 'shipclass_military':
            logging.debug('* ignored civilian ship: ' + ship.name)
            continue
        if 'is_designable' in token.properties and token.properties.get('is_designable') == 'no':
            logging.debug('* ignored indesignable ship: ' + ship.name)
            continue
        if 'is_space_station' in token.properties and token.properties.get('is_space_station') == 'yes':
            logging.debug('* ignored space station: ' + ship.name)
            continue
        if processor(ship):
            logging.debug('* discovered ship: ' + ship.name)
        else:
            logging.debug('* ignored ship: ' + ship.name)


def parse_tradition(tokens, processor: callable):
    for token in tokens:  # type: BlockToken
        if not isinstance(token, BlockToken):
            continue
        if 'adoption_bonus' not in token.properties or 'finish_bonus' not in token.properties or 'traditions' not in token.properties:
            continue

        category = TraditionCategory.from_token(token)
        if processor(category):
            logging.debug('* discovered traditions category: ' + category.name)
            for tradition in category.traditions:
                logging.debug('* discovered tradition: ' + category.traditions.get(tradition).name)
        else:
            logging.debug('* ignored traditions category: ' + category.name)
            for tradition in category.traditions:
                logging.debug('* ignored tradition: ' + category.traditions.get(tradition).name)


def filter_file(file_path: str, file_patterns: list = None) -> bool:
    if file_patterns is None:
        return True

    file_path = file_path.replace('\\', '/')
    for file_pattern in file_patterns:
        if re.search(file_pattern, file_path):
            return True

    return False


def traverse_zip(file_path: str, file_patterns: list = None):
    with ZipFile(file_path) as handler:
        for file_info in handler.infolist():  # type: ZipInfo
            file_zipname = file_path + os.path.sep + os.path.normpath(file_info.filename)
            if not file_info.is_dir() and filter_file(file_info.filename, file_patterns):
                logging.debug('-> reading zip-file %s...' % file_zipname)
                yield (file_zipname, handler.read(file_info.filename))


def traverse_directory(dir_path: str, file_patterns: list = None):
    for file_name in os.listdir(dir_path):
        if file_name == '.' or file_name == '..' or file_name.startswith('.'):
            continue
        file_path = os.path.join(dir_path, file_name)
        if os.path.isdir(file_path):
            yield from traverse_directory(file_path, file_patterns)
        elif os.path.isfile(file_path):
            _, file_ext = os.path.splitext(file_path)
            if file_ext == '.zip':
                yield from traverse_zip(file_path, file_patterns)
            elif filter_file(file_path, file_patterns):
                logging.debug('-> reading file %s...' % file_path)
                with open(file_path, mode='r', encoding='UTF-8', errors=None) as file_handler:
                    yield (file_path, file_handler.read())


def read_settings(settings_path) -> Settings:
    settings = Settings()
    for token in parse_settings(settings_path):
        if isinstance(token, EnumerationToken):
            if token.name == 'last_mods':
                settings.set('modules', [re.sub(r'mod/(?:ugc_)?([^.]+)\.mod', '\\1', module) for module in token])
            else:
                settings.set(token.name, list(token))
        elif isinstance(token, PropertyToken):
            settings.set(token.name, token.value)

    return settings


def get_module(file_path: str, modules_list: dict = None, cache: Cache = None) -> Module:
    # it my be /path/to/<module_id>/archive.zip
    # or my be /path/to/<module_id>/archive.zip/path/to/file.txt
    # or my be /path/to/<module_id>/path/to/file.txt
    module = None
    dir_list = file_path.split(os.path.sep)
    dir_list.reverse()
    for i, dir_name in enumerate(dir_list):
        if i == 0 or i == len(dir_list) - 1:
            continue

        if dir_name.isnumeric():
            module_id = int(dir_name)
            if modules_list is not None and module_id in modules_list:
                return modules_list.get(module_id)

            module = Module(module_id)
            module.name = detect_module(module_id, Module.url(module_id), cache)
            break
        elif dir_list[i + 1] == 'mod':
            settings_path = file_path[:file_path.rindex(os.sep + dir_name + os.sep) + 1]  + dir_name + '.mod'

            if os.path.exists(settings_path):
                module_id = dir_name
                if modules_list is not None and module_id in modules_list:
                    return modules_list.get(module_id)

                settings_data = read_settings(settings_path)
                if 'name' in settings_data:
                    module = Module(module_id)
                    module.name = settings_data.get('name')
                    break

    if module is None:
        module_id = 0
        if modules_list is not None and module_id in modules_list:
            return modules_list.get(module_id)

        module = Module(module_id)
        module.name = 'Stellaris'

    if modules_list is not None:
        modules_list[module.id] = module

    module.technologies = Technologies()
    module.buildings = Buildings()
    module.ships = Ships()
    module.traditions = TraditionCategories()

    return module


user_modules = None
if user_settings is not None:
    user_modules = read_settings(user_settings).get('modules')
cache_path = os.path.join(os.getcwd(), 'cache.json')
cache_data = Cache(cache_path)
modules_list = dict()

file_patterns = [
    r'common/technology/[\w-]+(?=\.txt)',
    r'common/buildings/[\w-]+(?=\.txt)',
    r'common/ship_sizes/[\w-]+(?=\.txt)',
    r'common/tradition_categories/[\w-]+(?=\.txt)'
]
for dir_path in dirs_list:
    logging.debug('-> traversing dir %s' % dir_path)

    for file_path, file_content in traverse_directory(dir_path, file_patterns):
        if isinstance(file_content, bytes):
            file_content = file_content.decode('UTF-8')
        try:
            tokens = parse_string(file_content)
        except ParseException as err:
            logging.error('Error occurred while parsing file %s: %s' % (file_path, err))
            continue

        module = get_module(file_path, modules_list, cache_data)
        parse_technology(tokens, module.technologies)
        parse_building(tokens, module.buildings)
        parse_ship(tokens, module.ships)
        parse_tradition(tokens, module.traditions)

ships = list()
templates = [
    GatheringTechnologyDataTemplate(),
    GatheringTraditionsDataTemplate(),
    DemolishBuildingRulesTemplate()
]
for module_id in modules_list:
    module = modules_list.get(module_id)  # type: Module
    if module_id and user_modules and str(module_id) not in user_modules:
        logging.info('... module %s skipped' % module)
        continue

    for technology in module.technologies.sorted():
        for template in templates:
            if template.supports(technology):
                template.process(technology, module)

    for building in module.buildings.sorted():
        for template in templates:
            if template.supports(building):
                template.process(building, module)

    for traditions in module.traditions.sorted():
        for template in templates:
            if template.supports(traditions):
                template.process(traditions, module)

    for ship in module.ships:
        if ship.name in ships:
            logging.info('... ship %s from module %s skipped' % (ship, module))
            continue
        ships.append(ship.name)
        logging.info('Discovered military ship "%s" from module %s' % (ship.name, module.name))

# Building Categories: 'amenity', 'army', 'government', 'manufacturing', 'pop_assembly', 'research', 'resource', 'trade', 'unity'
for template in templates:
    with open(template.name(), 'wt') as handler:
        handler.writelines(template.compile())
