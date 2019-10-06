#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import argparse
import logging
import urllib.request
from pprint import pprint
from urllib.error import URLError
from string import Template
from pyparsing import ParseException

from parsing import parse_string, parse_settings, BlockToken, EnumerationToken
from domains import Building, Buildings, Technology, Technologies, Ship, Ships, Module, Settings
from caching import Cache
from zipfile import ZipFile
from zipfile import ZipInfo

parser = argparse.ArgumentParser(description='Parse and extract data from Stellaris modules')
parser.add_argument('locations', type=str, help='Path to directory with module data', nargs='*', default=[os.getcwd()])
parser.add_argument('-l', '--log', type=str, help='Logging level')
arguments = parser.parse_args()

level = logging.DEBUG
if arguments.log is not None and hasattr(logging, arguments.log):
    level = getattr(logging, arguments.log)
logging.basicConfig(format='%(asctime)s: [%(levelname)s] %(message)s', level=level)

for i, dir_path in enumerate(arguments.locations):
    if not os.path.isabs(dir_path):
        arguments.locations[i] = os.path.realpath(dir_path)
    if not os.path.exists(dir_path):
        logging.error('Unable to find location "%s"' % dir_path)
        exit(1)
    if not os.path.isdir(dir_path):
        logging.error('The indicated location "%s" is not an directory' % dir_path)
        exit(1)
# arguments.locations = [os.path.abspath(os.path.join(os.getcwd(), '..', 'tmp'))]


def fetch_url(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def set_module_name(module: Module, cache: Cache = None) -> bool:
    module_id = str(module.id)
    if cache is not None and cache.has('modules', module_id):
        module.name = cache.get('modules', module_id)
        return True

    module_url = module.url
    page_content = None
    logging.debug('-> fetching module (%s) name from %s...' % (module_id, module_url))
    try:
        page_content = fetch_url(module_url).decode('UTF-8')
    except URLError as err:
        logging.error('Error occurred while fetching url %s: %s' % (module_url, err))
    except OSError as err:
        logging.error('Error occurred while fetching module data: %s' % err)

    if page_content is not None:
        module_name = re.search(r'<title>([^>]+)</title>', page_content).group(1)

        if module_name is not None:
            module_name = module_name.replace('Steam Workshop ::', '')
            module_name = module_name.strip()
            module.name = module_name
            logging.debug('-> fetched module (%s) name as "%s"' % (module_id, module_name))

            if cache is not None:
                cache.set(module_name, module_id, 'modules')
            return True

    return False

# s = '''
# '''
# t = parse_string(s)
# pprint(t)
# exit(0)


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
        if 'base_buildtime' not in token.properties:
            continue

        building = Building.from_token(token)
        if 'capital' in token.properties and token.properties.get('capital') == 'yes':
            logging.debug('* ignored capital building: ' + building.name)
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


def detect_module(file_path: str, cache: Cache = None) -> Module:
    # it my be /path/to/<module_id>/archive.zip
    # or my be /path/to/<module_id>/archive.zip/path/to/file.txt
    # or my be /path/to/<module_id>/path/to/file.txt
    module = None
    dir_list = file_path.split(os.path.sep)
    dir_list.reverse()
    for dir_name in dir_list:
        if dir_name.isnumeric():
            module = Module(int(dir_name))
            set_module_name(module, cache)
            break
        elif dir_name == 'aoe':
            module = Module(1)
            module.name = 'Anthem of Eternity'
            break

    if module is None:
        module = Module(0)
        module.name = 'Stellaris'

    return module


def read_settings(settings_path) -> Settings:
    settings = Settings()
    for token in parse_settings(settings_path):
        if isinstance(token, EnumerationToken):
            if token.name == 'last_mods':
                for module in token:
                    module = re.sub(r'mod/(?:ugc_)?([^.]+)\.mod', '\\1', str(module))
                    if module == 'aoe':
                        module = 1
                    else:
                        module = int(module)
                    settings.add_module(module, True)

    return settings


user_settings = read_settings("C:\\Users\\Sergey\\Documents\\Paradox Interactive\\Stellaris\\settings.txt")
cache_path = os.path.join(os.getcwd(), 'cache.json')
cache_data = Cache(cache_path)

modules_list = dict()
file_patterns = [
    r'common/technology/[\w-]+(?=\.txt)',
    r'common/buildings/[\w-]+(?=\.txt)',
    r'common/ship_sizes/[\w-]+(?=\.txt)',
    # r'\.txt$'
]
for dir_path in arguments.locations:
    logging.debug('-> traversing dir %s' % dir_path)

    for file_path, file_content in traverse_directory(dir_path, file_patterns):
        if isinstance(file_content, bytes):
            file_content = file_content.decode('UTF-8')
        try:
            tokens = parse_string(file_content)
        except ParseException as err:
            logging.error('Error occurred while parsing file %s: %s' % (file_path, err))
            continue

        module = detect_module(file_path, cache_data)
        if module.id not in modules_list:
            modules_list[module.id] = (module, Technologies(), Buildings(), Ships())

        parse_technology(tokens, modules_list[module.id][1])
        parse_building(tokens, modules_list[module.id][2])
        parse_ship(tokens, modules_list[module.id][3])


output = list()

tpl_checker = Template('''\
    if = {
        limit = {
            has_technology = "$name"
        }
$setters
    }\
''')
tpl_setter = Template('''\
        change_variable = {
            which = "espionage_data_technology_count_$tag"
            value = 1
        }\
''')

technology_areas = set()
# Technology Categories: 'biology', 'computing', 'field_manipulation', 'industry', 'materials', 'military_theory', 'new_worlds', 'particles', 'propulsion', 'psionics', 'statecraft', 'voidcraft'
technology_categories = set()
for module_id in modules_list:
    module, technologies, buildings, ships = modules_list.get(module_id)
    if module_id != 0 and not user_settings.has_module(module):
        logging.info('Module %s not enabled' % module)
        continue

    for technology in technologies:
        technology_areas.add(technology.area)
        for category in technology.categories:
            technology_categories.add(category)

    output.append('    # Module %s: %d technologies discovered' % (module, len(technologies)))
    for technology in technologies:
        setters = list()
        setters.append(tpl_setter.substitute(tag='area_' + technology.area))
        if technology.is_dangerous:
            setters.append(tpl_setter.substitute(tag='type_dangerous'))
        elif technology.is_rare:
            setters.append(tpl_setter.substitute(tag='type_rare'))
        for category in technology.categories:
            setters.append(tpl_setter.substitute(tag='category_' + category))
        if len(setters) > 0:
            output.append(tpl_checker.substitute(name=technology.name, setters="\n".join(setters)))

    for ship in ships:
        logging.info('Ship "%s" from %s' % (ship.name, module.name))

# Building Categories: 'amenity', 'army', 'government', 'manufacturing', 'pop_assembly', 'research', 'resource', 'trade', 'unity'
template = Template('''\
    set_variable = {
        which = "espionage_data_technology_count_$tag"
        value = 0
    }\
''')
for area in technology_areas:
    output.insert(0, template.substitute(tag='area_' + area))
    logging.info('Technology area: %s' % area)
for category in technology_categories:
    output.insert(0, template.substitute(tag='category_' + category))
    logging.info('Technology category: %s' % category)
for type in ('rare', 'dangerous'):
    output.insert(0, template.substitute(tag='type_' + type))

with open('output.txt', 'wt') as handler:
    handler.write('intelligence_gather_technology_data = {')
    handler.write("\n")
    for line in output:
        handler.write(line)
        handler.write("\n")
    handler.write('}')


