#!/usr/bin/env python

"""
This module implements input and output processing from Nwchem.
"""

from __future__ import division

__author__ = "Shyue Ping Ong"
__copyright__ = "Copyright 2012, The Materials Project"
__version__ = "0.1"
__maintainer__ = "Shyue Ping Ong"
__email__ = "shyuep@gmail.com"
__date__ = "6/5/13"


import re
from string import Template

from pymatgen.core import Molecule
import pymatgen.core.physical_constants as phyc
from pymatgen.util.io_utils import zopen
from pymatgen.serializers.json_coders import MSONable


class NwTask(MSONable):
    """
    Base task for Nwchem.
    """

    theories = {"g3gn": "some description",
                "scf": "Hartree-Fock",
                "dft": "DFT",
                "sodft": "Spin-Orbit DFT",
                "mp2": "MP2 using a semi-direct algorithm",
                "direct_mp2": "MP2 using a full-direct algorithm",
                "rimp2": "MP2 using the RI approximation",
                "ccsd": "Coupled-cluster single and double excitations",
                "ccsd(t)": "Coupled-cluster linearized triples approximation",
                "ccsd+t(ccsd)": "Fourth order triples contribution",
                "mcscf": "Multiconfiguration SCF",
                "selci": "Selected CI with perturbation correction",
                "md": "Classical molecular dynamics simulation",
                "pspw": "Pseudopotential plane-wave DFT for molecules and "
                        "insulating solids using NWPW",
                "band": "Pseudopotential plane-wave DFT for solids using NWPW",
                "tce": "Tensor Contraction Engine"}

    operations = {"energy": "Evaluate the single point energy.",
                  "gradient": "Evaluate the derivative of the energy with "
                              "respect to nuclear coordinates.",
                  "optimize": "Minimize the energy by varying the molecular "
                              "structure.",
                  "saddle": "Conduct a search for a transition state (or "
                            "saddle point).",
                  "hessian": "Compute second derivatives.",
                  "frequencies": "Compute second derivatives and print out an "
                                 "analysis of molecular vibrations.",
                  "freq": "Same as frequencies.",
                  "vscf": "Compute anharmonic contributions to the "
                          "vibrational modes.",
                  "property": "Calculate the properties for the wave "
                              "function.",
                  "dynamics": "Perform classical molecular dynamics.",
                  "thermodynamics": "Perform multi-configuration "
                                    "thermodynamic integration using "
                                    "classical MD."}

    def __init__(self, charge, spin_multiplicity, basis_set,
                 title=None, theory="dft", operation="optimize",
                 theory_directives=None):
        """
        Very flexible arguments to support many types of potential setups.
        Users should use more friendly static methods unless they need the
        flexibility.

        Args:
            charge:
                Charge of the molecule. If None, charge on molecule is used.
                Defaults to None. This allows the input file to be set a
                charge independently from the molecule itself.
            spin_multiplicity:
                Spin multiplicity of molecule. Defaults to None,
                which means that the spin multiplicity is set to 1 if the
                molecule has no unpaired electrons and to 2 if there are
                unpaired electrons.
            basis_set:
                The basis set used for the task as a dict. E.g.,
                {"C": "6-311++G**", "H": "6-31++G**"}.
            title:
                Title for the task. Defaults to None, which means a title
                based on the theory and operation of the task is
                autogenerated.
            theory:
                The theory used for the task. Defaults to "dft".
            operation:
                The operation for the task. Defaults to "optimize".

            theory_directives:
                A dict of theory directives. For example,
                if you are running dft calculations, you may specify the
                exchange correlation functional using {"xc": "b3lyp"}.
        """
        #Basic checks.
        if theory.lower() not in NwTask.theories.keys():
            raise NwInputError("Invalid theory {}".format(theory))

        if operation.lower() not in NwTask.operations.keys():
            raise NwInputError("Invalid operation {}".format(operation))
        self.charge = charge
        self.spin_multiplicity = spin_multiplicity
        self.title = title if title is not None else "{} {}".format(theory,
                                                                    operation)
        self.theory = theory
        self.basis_set = basis_set

        self.operation = operation
        self.theory_directives = theory_directives \
            if theory_directives is not None else {}

    def __str__(self):
        bset_spec = []
        for el, bset in self.basis_set.items():
            bset_spec.append(" {} library \"{}\"".format(el, bset))

        theory_spec = []
        if self.theory_directives:
            theory_spec.append("{}".format(self.theory))
            for k, v in self.theory_directives.items():
                theory_spec.append(" {} {}".format(k, v))
            theory_spec.append("end")

        t = Template("""title "$title"
charge $charge
basis
$bset_spec
end
$theory_spec
task $theory $operation""")

        return t.substitute(
            title=self.title, charge=self.charge,
            bset_spec="\n".join(bset_spec),
            theory_spec="\n".join(theory_spec),
            theory=self.theory, operation=self.operation)

    @property
    def to_dict(self):
        return {"@module": self.__class__.__module__,
                "@class": self.__class__.__name__,
                "charge": self.charge,
                "spin_multiplicity": self.spin_multiplicity,
                "title": self.title, "theory": self.theory,
                "operation": self.operation, "basis_set": self.basis_set,
                "theory_directives": self.theory_directives}

    @classmethod
    def from_dict(cls, d):
        return NwTask(charge=d["charge"],
                      spin_multiplicity=d["spin_multiplicity"],
                      title=d["title"], theory=d["theory"],
                      operation=d["operation"], basis_set=d["basis_set"],
                      theory_directives=d["theory_directives"])

    @classmethod
    def from_molecule(cls, mol, charge=None, spin_multiplicity=None,
                      basis_set="6-31g", title=None, theory="scf",
                      operation="optimize", theory_directives=None):
        """
        Very flexible arguments to support many types of potential setups.
        Users should use more friendly static methods unless they need the
        flexibility.

        Args:
            mol:
                Input molecule
            charge:
                Charge of the molecule. If None, charge on molecule is used.
                Defaults to None. This allows the input file to be set a
                charge independently from the molecule itself.
            spin_multiplicity:
                Spin multiplicity of molecule. Defaults to None,
                which means that the spin multiplicity is set to 1 if the
                molecule has no unpaired electrons and to 2 if there are
                unpaired electrons.
            basis_set:
                The basis set to be used as string or a dict. E.g.,
                {"C": "6-311++G**", "H": "6-31++G**"} or "6-31G". If string,
                same basis set is used for all elements.
            title:
                Title for the task. Defaults to None, which means a title
                based on the theory and operation of the task is
                autogenerated.
            theory:
                The theory used for the task. Defaults to "dft".
            operation:
                The operation for the task. Defaults to "optimize".

            theory_directives:
                A dict of theory directives. For example,
                if you are running dft calculations, you may specify the
                exchange correlation functional using {"xc": "b3lyp"}.
        """
        title = title if title is not None else "{} {} {}".format(
            re.sub("\s", "", mol.formula), theory, operation)

        charge = charge if charge is not None else mol.charge
        nelectrons = - charge + mol.charge + mol.nelectrons
        if spin_multiplicity is not None:
            spin_multiplicity = spin_multiplicity
            if (nelectrons + spin_multiplicity) % 2 != 1:
                raise ValueError(
                    "Charge of {} and spin multiplicity of {} is"
                    " not possible for this molecule".format(
                        charge, spin_multiplicity))
        elif charge == mol.charge:
            spin_multiplicity = mol.spin_multiplicity
        else:
            spin_multiplicity = 1 if nelectrons % 2 == 0 else 2

        elements = set(mol.composition.get_el_amt_dict().keys())
        if isinstance(basis_set, basestring):
            basis_set = {el: basis_set for el in elements}

        return NwTask(charge, spin_multiplicity, basis_set,
                      title=title, theory=theory, operation=operation,
                      theory_directives=theory_directives)


    @classmethod
    def dft_task(cls, mol, xc="b3lyp", **kwargs):
        """
        A class method for quickly creating DFT tasks.

        Args:
            mol:
                Input molecule
            xc:
                Exchange correlation to use.
            \*\*kwargs:
                Any of the other kwargs supported by NwTask. Note the theory
                is always "dft" for a dft task.
        """
        t = NwTask.from_molecule(mol, theory="dft", **kwargs)
        t.theory_directives.update({"xc": xc,
                                    "mult": t.spin_multiplicity})
        return t


class NwInput(MSONable):
    """
    An object representing a Nwchem input file, which is essentially a list
    of tasks on a particular molecule.
    """

    def __init__(self, mol, tasks, directives=None,
                 geometry_options=("units", "angstroms")):
        """
        Args:
            mol:
                Input molecule. If molecule is a single string, it is used as a
                direct input to the geometry section of the Gaussian input
                file.
            tasks:
                List of NwTasks.
            directives:
                List of root level directives as tuple. E.g.,
                [("start", "water"), ("print", "high")]
            geometry_options:
                Additional list of options to be supplied to the geometry.
                E.g., ["units", "angstroms", "noautoz"]. Defaults to
                ("units", "angstroms").
        """
        self._mol = mol
        self.directives = directives if directives is not None else []
        self.tasks = tasks
        self.geometry_options = geometry_options

    @property
    def molecule(self):
        """
        Returns molecule associated with this GaussianInput.
        """
        return self._mol

    def __str__(self):
        o = []
        for d in self.directives:
            o.append("{} {}".format(d[0], d[1]))
        o.append("geometry "
                 + " ".join(self.geometry_options))
        for site in self._mol:
            o.append(" {} {} {} {}".format(site.specie.symbol, site.x, site.y,
                                           site.z))
        o.append("end\n")
        for t in self.tasks:
            o.append(str(t))
            o.append("")
        return "\n".join(o)

    def write_file(self, filename):
        with zopen(filename, "w") as f:
            f.write(self.__str__())

    @property
    def to_dict(self):
        return {
            "mol": self._mol.to_dict,
            "tasks": [t.to_dict for t in self.tasks],
            "directives": [list(t) for t in self.directives],
            "geometry_options": list(self.geometry_options)
        }

    @classmethod
    def from_dict(cls, d):
        return NwInput(Molecule.from_dict(d["mol"]),
                       tasks=[NwTask.from_dict(dt) for dt in d["tasks"]],
                       directives=[tuple(li) for li in d["directives"]],
                       geometry_options=d["geometry_options"])

    @classmethod
    def from_string(cls, string_input):
        """
        Read an NwInput from a string. Currently tested to work with
        files generated from this class itself.

        Args:
            string_input:
                string_input to parse.

        Returns:
            NwInput object
        """
        directives = []
        tasks = []
        charge = None
        spin_multiplicity = None
        title = None
        basis_set = None
        theory_directives = {}
        geom_options = None
        lines = string_input.strip().split("\n")
        while len(lines) > 0:
            l = lines.pop(0).strip()
            if l == "":
                continue

            toks = l.split()
            if toks[0].lower() == "geometry":
                geom_options = toks[1:]
                #Parse geometry
                l = lines.pop(0).strip()
                species = []
                coords = []
                while l.lower() != "end":
                    toks = l.split()
                    species.append(toks[0])
                    coords.append(map(float, toks[1:]))
                    l = lines.pop(0).strip()
                mol = Molecule(species, coords)
            elif toks[0].lower() == "charge":
                charge = int(toks[1])
            elif toks[0].lower() == "title":
                title = l[5:].strip().strip("\"")
            elif toks[0].lower() == "basis":
                #Parse basis sets
                l = lines.pop(0).strip()
                basis_set = {}
                while l.lower() != "end":
                    toks = l.split()
                    basis_set[toks[0]] = toks[-1].strip("\"")
                    l = lines.pop(0).strip()
            elif toks[0].lower() in NwTask.theories:
                #Parse theory directives.
                theory = toks[0].lower()
                l = lines.pop(0).strip()
                theory_directives[theory] = {}
                while l.lower() != "end":
                    toks = l.split()
                    theory_directives[theory][toks[0]] = toks[-1]
                    if toks[0] == "mult":
                        spin_multiplicity = float(toks[1])
                    l = lines.pop(0).strip()
            elif toks[0].lower() == "task":
                tasks.append(
                    NwTask(charge=charge,
                           spin_multiplicity=spin_multiplicity,
                           title=title, theory=toks[1],
                           operation=toks[2], basis_set=basis_set,
                           theory_directives=theory_directives.get(toks[1])))
            else:
                directives.append(l.strip().split())

        return NwInput(mol, tasks=tasks, directives=directives,
                       geometry_options=geom_options)

    @classmethod
    def from_file(cls, filename):
        """
        Read an NwInput from a file. Currently tested to work with
        files generated from this class itself.

        Args:
            filename:
                Filename to parse.

        Returns:
            NwInput object
        """
        with zopen(filename) as f:
            return cls.from_string(f.read())


class NwInputError(Exception):
    """
    Error class for NwInput.
    """
    pass


class NwOutput(object):
    """
    A Nwchem output file parser. Very basic for now - supports only dft and
    only parses energies and geometries. Please note that Nwchem typically
    outputs energies in either au or kJ/mol. All energies are converted to
    eV in the parser.
    """

    def __init__(self, filename):
        self.filename = filename

        with zopen(filename) as f:
            data = f.read()

        chunks = re.split("NWChem Input Module", data)
        if re.search("CITATION", chunks[-1]):
            chunks.pop()
        preamble = chunks.pop(0)
        self.job_info = self._parse_preamble(preamble)
        self.data = map(self._parse_job, chunks)

    def _parse_preamble(self, preamble):
        info = {}
        for l in preamble.split("\n"):
            toks = l.split("=")
            if len(toks) > 1:
                info[toks[0].strip()] = toks[-1].strip()
        return info

    def _parse_job(self, output):
        energy_patt = re.compile("Total \w+ energy\s+=\s+([\.\-\d]+)")
        coord_patt = re.compile("\d+\s+(\w+)\s+[\.\-\d]+\s+([\.\-\d]+)\s+"
                                "([\.\-\d]+)\s+([\.\-\d]+)")
        corrections_patt = re.compile("([\w\-]+ correction to \w+)\s+="
                                      "\s+([\.\-\d]+)")
        preamble_patt = re.compile("(No. of atoms|No. of electrons"
                                   "|SCF calculation type|Charge|Spin "
                                   "multiplicity)\s*:\s*(\S+)")
        error_defs = {
            "calculations not reaching convergence": "Bad convergence",
            "geom_binvr: #indep variables incorrect": "autoz error"}

        data = {}
        energies = []
        corrections = {}
        molecules = []
        species = []
        coords = []
        errors = []
        basis_set = {}
        parse_geom = False
        parse_bset = False
        job_type = ""
        for l in output.split("\n"):
            for e, v in error_defs.items():
                if l.find(e) != -1:
                    errors.append(v)
            if parse_geom:
                if l.strip() == "Atomic Mass":
                    molecules.append(Molecule(species, coords))
                    species = []
                    coords = []
                    parse_geom = False
                else:
                    m = coord_patt.search(l)
                    if m:
                        species.append(m.group(1).capitalize())
                        coords.append([float(m.group(2)), float(m.group(3)),
                                       float(m.group(4))])
            elif parse_bset:
                if l.strip() == "":
                    parse_bset = False
                else:
                    toks = l.split()
                    if toks[0] != "Tag" and not re.match("\-+", toks[0]):
                        basis_set[toks[0]] = dict(zip(bset_header[1:],
                                                      toks[1:]))
                    elif toks[0] == "Tag":
                        bset_header = toks
                        bset_header.pop(4)
                        bset_header = [h.lower() for h in bset_header]
            else:
                m = energy_patt.search(l)
                if m:
                    energies.append(float(m.group(1)) * phyc.Ha_eV)
                    continue

                m = preamble_patt.search(l)
                if m:
                    try:
                        val = int(m.group(2))
                    except ValueError:
                        val = m.group(2)
                    k = m.group(1).replace("No. of ", "n").replace(" ", "_")
                    data[k.lower()] = val
                elif l.find("Geometry \"geometry\"") != -1:
                    parse_geom = True
                elif l.find("Summary of \"ao basis\"") != -1:
                    parse_bset = True
                elif job_type == "" and l.strip().startswith("NWChem"):
                    job_type = l.strip()
                else:
                    m = corrections_patt.search(l)
                    if m:
                        corrections[m.group(1)] = float(m.group(2)) / \
                            phyc.EV_PER_ATOM_TO_KJ_PER_MOL

        data.update({"job_type": job_type, "energies": energies,
                     "corrections": corrections,
                     "molecules": molecules,
                     "basis_set": basis_set,
                     "errors": errors,
                     "has_error": len(errors) > 0})

        return data
