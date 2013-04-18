#!/usr/bin/python
import unittest
import os
import pymatgen

from pymatgen.io.feffio_set import FeffInputSet
from pymatgen.io.feffio import FeffPot
from pymatgen.io.cifio import CifParser

test_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                        'test_files')
cif_file = 'CoO19128.cif'
central_atom = 'O'
cif_path = os.path.join(test_dir, cif_file)
r = CifParser(cif_path)
structure = r.get_structures()[0]
x = FeffInputSet("MaterialsProject")


class FeffInputSetTest(unittest.TestCase):

    header_string = """* This FEFF.inp file generated by pymatgen
TITLE Source:  CoO19128
TITLE Structure Summary:  Co2 O2
TITLE Reduced formula:  CoO
TITLE space group: (Cmc2_1), space number:  (36)
TITLE abc:  3.297078   3.297078   5.254213
TITLE angles: 90.000000  90.000000 120.000000
TITLE sites: 4
* 1 Co     0.666666     0.333332     0.496324
* 2 Co     0.333333     0.666667     0.996324
* 3 O     0.666666     0.333332     0.878676
* 4 O     0.333333     0.666667     0.378675"""

    def test_get_header(self):
        header = FeffInputSet.get_header(x, structure, 'CoO19128')
        print '\n\n'
        print header
        print '\n\nheader_string'
        print FeffInputSetTest.header_string
        self.assertEqual(FeffInputSetTest.header_string.splitlines(),
                         header.splitlines(), "Failed to read HEADER file")

    def test_getfefftags(self):
        tags = FeffInputSet.get_feff_tags(x, "XANES")
        self.assertEqual(tags["COREHOLE"], "FSR",
                         "Failed to read PARAMETERS file")

    def test_get_feffPot(self):
        POT = FeffInputSet.get_feff_pot(x, structure, central_atom)
        d, dr = FeffPot.pot_dict_from_string(POT)

        self.assertEqual(d['Co'], 1, "Wrong symbols read in for FeffPot")

    def test_get_feffAtoms(self):
        ATOMS = FeffInputSet.get_feff_atoms(x, structure, central_atom)
        self.assertEqual(ATOMS.splitlines()[3].split()[4], central_atom,
                         "failed to create ATOMS string")

if __name__ == '__main__':
    unittest.main()
