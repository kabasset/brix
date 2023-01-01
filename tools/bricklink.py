# SPDX-Copyright: 2023 Antoine Basset
# SPDX-License-Identifier: LGPL-3.0-or-later

from argparse import ArgumentParser
from collections import defaultdict, namedtuple
from copy import copy
import json
import re


Element = namedtuple('Element', ['color', 'part'])


class Inventory:

    def __init__(self):
        self._items = defaultdict(lambda : 0)

    def __add__(self, element):
        self._items[element] += 1
        return self
    
    def __iter__(self):
        return iter(self._items)
    
    def __getitem__(self, key):
        return self._items[key]
    
    def __str__(self):
        return str(self._items)
    
    def __len__(self):
        return sum(self._items.values())
    
    def elements(self):
        return self._items.keys()
    
    def colors(self):
        return set(e.color for e in self.elements())
    
    def parts(self):
        return set(e.part for e in self.elements())


class LdrawReader:

    def __init__(self, filename):
        self.filename = filename
        self._f = None
        self.inventory = Inventory()
    
    def __enter__(self):
        self._f = open(self.filename)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._f.close()
    
    def read(self):
        for l in self._f:
            l = l.strip()
            if self.is_element(l):
                self.read_element(l)
        return self.inventory
    
    def is_element(self, line):
        return line.startswith('1') and line.endswith('.dat')
    
    def read_element(self, line):
        chunks = line.strip().split()
        color = chunks[1]
        part = chunks[-1].split('.')[0]
        element = Element(color, part)
        self.inventory += element
        return element


class BricklinkWriter:
    
    def __init__(self, filename, mapping=None):
        self.filename = filename
        self._f = None
        self._color_mapping = {} if mapping is None else mapping['colors']
        self._part_mapping = {} if mapping is None else mapping['parts']
    
    def __enter__(self):
        self._f = open(self.filename, 'x')
        self._f.write('<INVENTORY>\n')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._f.write('</INVENTORY>')
        self._f.close()
    
    def write(self, inventory):
        for e in inventory:
            self.write_item(e, inventory[e])
    
    def write_item(self, element, quantity):
        color = self.map_color(element.color)
        part = self.map_part(element.part)
        content = (
            f'  <ITEM>\n'
            f'    <ITEMTYPE>P</ITEMTYPE>\n'
            f'    <COLOR>{color}</COLOR>\n'
            f'    <ITEMID>{part}</ITEMID>\n'
            f'    <MINQTY>{quantity}</MINQTY>\n'
            f'    <CONDITION>N</CONDITION>\n'
            f'  </ITEM>\n')
        self._f.write(content)
    
    def map_color(self, color):
        if not color in self._color_mapping:
            print(f'No mapping for color: {color}')
        return self._color_mapping.get(color, color)
    
    def map_part(self, part):
        for key in self._part_mapping:
            part = re.sub(key, self._part_mapping[key], part)
        return part


def main(ldraw, mapping):
    
    print(f'Reading LDraw file: {ldraw}')
    with LdrawReader(ldraw) as reader:
        inventory = reader.read()
    print(f'- Number of different elements: {len(inventory.elements())}')
    print(f'- Number of different colors: {len(inventory.colors())}')
    print(f'- Number of different parts: {len(inventory.parts())}')
    print(f'- Total number of elements: {len(inventory)}')
    
    bricklink = ldraw + '.xml'
    print(f'Writing BrickLink file: {bricklink}')
    if mapping is not None:
        with open(mapping) as f:
            mapping = json.load(f)
    with BricklinkWriter(bricklink, mapping) as writer:
        writer.write(inventory)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('ldraw', help='The input LDraw file')
    parser.add_argument('--split', action='store_true', help='Split by submodel')
    parser.add_argument('--map', help='LDraw-BrickLink mapping')
    args = parser.parse_args()
    main(args.ldraw, args.map)

