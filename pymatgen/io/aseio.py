#!/usr/bin/env python

'''
This module provides conversion between the Atomic Simulation Environment
Atoms object and pymatgen Structure objects.  It also includes an adaptor
for spglib for spacegroup determination
'''

from __future__ import division

__author__="Shyue Ping Ong"
__copyright__ = "Copyright 2012, The Materials Project"
__version__ = "0.1"
__maintainer__ = "Shyue Ping Ong"
__email__ = "shyue@mit.edu"
__date__ = "Mar 8, 2012"

from pymatgen.core.structure import Structure
from ase import Atoms
from pyspglib import spglib

class AseAtomsAdaptor(object):
    '''
    classdocs
    '''
    
    @staticmethod
    def get_atoms(structure):
        """
        Returns ASE Atoms object from pymatgen structure
        """
        symbols = [site.specie.symbol for site in structure]
        positions = [site.coords for site in structure]
        cell = structure.lattice.matrix
        return Atoms(symbols=symbols, positions=positions, pbc = True, cell=cell)

    @staticmethod
    def get_structure(atoms):
        """
        Returns pymatgen structure from ASE Atoms
        """
        symbols = atoms.get_chemical_symbols()
        positions = atoms.get_positions()
        lattice = atoms.get_cell()
        return Structure(lattice, symbols, positions, coords_are_cartesian = True)

class SpglibAdaptor(object):
    
    def __init__(self, structure, symprec = 1e-5):
        self._symprec = symprec
        self._atoms = AseAtomsAdaptor.get_atoms(structure)
    
    def get_spacegroup(self):
        return spglib.get_spacegroup(self._atoms, symprec = self._symprec)

    
if __name__ == "__main__":
    from pymatgen.io.vaspio import Poscar
    p = Poscar.from_file('tests/vasp_testfiles/POSCAR')
    print p.struct
    atoms = AseAtomsAdaptor.get_atoms(p.struct)
    print dir(atoms)
    print atoms.positions
    print atoms.get_chemical_symbols()
    print AseAtomsAdaptor.get_structure(atoms)
    
    sg = SpglibAdaptor(p.struct)
    print sg.get_spacegroup()