"""NCERT Class 12 Physics concepts used as the prediction units.

Official theory marks below are the combined unit-group totals published in the
CBSE Class XII Physics curriculum for 2025-26 (code 042). CBSE does not publish
a separate mark total for every chapter, so this taxonomy does not invent one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnitGroup:
    id: str
    name: str
    marks: int
    chapters: tuple[int, ...]


@dataclass(frozen=True)
class Concept:
    id: str
    name: str
    chapter_number: int
    chapter: str
    unit_group: str
    keywords: tuple[str, ...]
    study_hours: float
    typical_marks: float


UNIT_GROUPS: tuple[UnitGroup, ...] = (
    UnitGroup("I-II", "Electrostatics and current electricity", 16, (1, 2, 3)),
    UnitGroup("III-IV", "Magnetism, induction, and alternating current", 17, (4, 5, 6, 7)),
    UnitGroup("V-VI", "Electromagnetic waves and optics", 18, (8, 9, 10)),
    UnitGroup("VII-VIII", "Dual nature, atoms, and nuclei", 12, (11, 12, 13)),
    UnitGroup("IX", "Semiconductor electronics", 7, (14,)),
)

CHAPTERS: dict[int, str] = {
    1: "Electric Charges and Fields",
    2: "Electrostatic Potential and Capacitance",
    3: "Current Electricity",
    4: "Moving Charges and Magnetism",
    5: "Magnetism and Matter",
    6: "Electromagnetic Induction",
    7: "Alternating Current",
    8: "Electromagnetic Waves",
    9: "Ray Optics and Optical Instruments",
    10: "Wave Optics",
    11: "Dual Nature of Radiation and Matter",
    12: "Atoms",
    13: "Nuclei",
    14: "Semiconductor Electronics: Materials, Devices and Simple Circuits",
}

THEORY_MARKS = 70

# study_hours and typical_marks are planning weights for the expected-value
# plan. They are not CBSE mark allocations.
_RAW: tuple[tuple[str, str, int, tuple[str, ...], float, float], ...] = (
    (
        "ch01.coulombs_law",
        "Coulomb's law and superposition",
        1,
        ("coulomb's law", "coulombs law", "superposition principle", "point charges"),
        2.5,
        3,
    ),
    (
        "ch01.electric_field",
        "Electric field and field lines",
        1,
        ("electric field lines", "field due to a point charge", "electric field due"),
        2.0,
        2,
    ),
    (
        "ch01.dipole",
        "Electric dipole and torque",
        1,
        ("electric dipole", "torque on a dipole", "dipole moment"),
        2.0,
        3,
    ),
    (
        "ch01.gauss_law",
        "Gauss's theorem and its applications",
        1,
        (
            "gauss's theorem",
            "gauss's law",
            "gauss law",
            "gaussian surface",
            "infinitely long straight wire",
            "infinite plane sheet",
        ),
        3.0,
        5,
    ),
    (
        "ch02.potential",
        "Electric potential and equipotential surfaces",
        2,
        ("electric potential", "equipotential", "potential due to a point charge", "potential difference"),
        2.5,
        3,
    ),
    (
        "ch02.capacitance",
        "Capacitance, combination, and energy stored",
        2,
        (
            "parallel plate capacitor",
            "energy stored in a capacitor",
            "capacitors in series",
            "combination of capacitors",
            "capacitance",
        ),
        3.0,
        5,
    ),
    (
        "ch02.dielectrics",
        "Dielectrics and polarisation",
        2,
        ("dielectric", "electric polarization", "electric polarisation", "bound charges"),
        1.5,
        2,
    ),
    (
        "ch03.drift_ohm",
        "Drift velocity, Ohm's law, and resistivity",
        3,
        ("drift velocity", "ohm's law", "ohms law", "resistivity", "temperature dependence of resistance"),
        2.5,
        3,
    ),
    (
        "ch03.cells_kirchhoff",
        "Cells, internal resistance, and Kirchhoff's rules",
        3,
        ("kirchhoff", "internal resistance", "emf of a cell", "combination of cells"),
        3.0,
        5,
    ),
    (
        "ch03.wheatstone",
        "Wheatstone bridge",
        3,
        ("wheatstone",),
        1.5,
        2,
    ),
    (
        "ch04.biot_savart",
        "Biot-Savart law",
        4,
        ("biot-savart", "biot savart", "biot–savart"),
        2.5,
        3,
    ),
    (
        "ch04.ampere",
        "Ampere's law, straight wire, and solenoid",
        4,
        ("ampere's law", "amperes law", "ampere’s law", "long solenoid", "straight solenoid"),
        2.5,
        3,
    ),
    (
        "ch04.lorentz",
        "Force on a charge and on a current-carrying conductor",
        4,
        ("lorentz force", "force on a moving charge", "force between two parallel", "definition of ampere"),
        2.5,
        3,
    ),
    (
        "ch04.galvanometer",
        "Current loop, galvanometer, ammeter, and voltmeter",
        4,
        (
            "moving coil galvanometer",
            "current sensitivity",
            "conversion to ammeter",
            "into a voltmeter",
            "magnetic dipole moment",
        ),
        3.0,
        5,
    ),
    (
        "ch05.bar_magnet",
        "Bar magnet as a dipole",
        5,
        ("bar magnet", "magnetic dipole", "magnetic field lines"),
        2.0,
        3,
    ),
    (
        "ch05.materials",
        "Dia-, para-, and ferromagnetism",
        5,
        ("ferromagnetic", "paramagnetic", "diamagnetic", "magnetisation", "magnetization"),
        1.5,
        2,
    ),
    (
        "ch06.faraday_lenz",
        "Faraday's laws and Lenz's law",
        6,
        ("faraday's law", "faradays law", "faraday’s law", "lenz's law", "lenz’s law", "induced emf"),
        3.0,
        5,
    ),
    (
        "ch06.inductance",
        "Self-induction and mutual induction",
        6,
        ("self-induction", "self induction", "mutual induction", "self-inductance", "mutual inductance"),
        2.5,
        3,
    ),
    (
        "ch07.lcr",
        "RMS values, reactance, and LCR circuits",
        7,
        ("lcr", "reactance", "impedance", "root mean square", "rms value", "phasor"),
        3.0,
        5,
    ),
    (
        "ch07.power",
        "Resonance, power factor, and wattless current",
        7,
        ("power factor", "wattless", "resonance frequency", "series resonance"),
        2.0,
        3,
    ),
    (
        "ch07.transformer",
        "AC generator and transformer",
        7,
        ("transformer", "ac generator", "step-up", "step-down", "step up transformer", "step down transformer"),
        2.5,
        3,
    ),
    (
        "ch08.displacement",
        "Displacement current and electromagnetic waves",
        8,
        ("displacement current", "electromagnetic wave", "transverse nature"),
        2.0,
        2,
    ),
    (
        "ch08.spectrum",
        "Electromagnetic spectrum",
        8,
        ("electromagnetic spectrum", "radio waves", "microwaves", "gamma rays"),
        1.5,
        2,
    ),
    (
        "ch09.mirrors",
        "Spherical mirrors and the mirror formula",
        9,
        ("mirror formula", "spherical mirror", "concave mirror", "convex mirror"),
        2.5,
        3,
    ),
    (
        "ch09.tir",
        "Refraction, total internal reflection, and optical fibre",
        9,
        ("total internal reflection", "optical fibre", "optical fiber"),
        2.0,
        3,
    ),
    (
        "ch09.lenses",
        "Thin lenses and the lens maker's formula",
        9,
        ("lens maker", "lens maker's", "thin lens", "power of a lens", "lenses in contact"),
        3.0,
        5,
    ),
    (
        "ch09.prism",
        "Refraction through a prism",
        9,
        ("angle of minimum deviation", "refraction through a prism", "glass prism"),
        2.0,
        3,
    ),
    (
        "ch09.instruments",
        "Microscope and astronomical telescope",
        9,
        ("astronomical telescope", "compound microscope", "magnifying power"),
        2.5,
        3,
    ),
    (
        "ch10.huygens",
        "Huygens' principle",
        10,
        ("huygens", "huygen's", "wavefront", "wave front"),
        2.0,
        3,
    ),
    (
        "ch10.ydse",
        "Young's double slit and fringe width",
        10,
        ("young's double slit", "young double slit", "double slit", "fringe width"),
        3.0,
        5,
    ),
    (
        "ch10.diffraction",
        "Single-slit diffraction",
        10,
        ("single slit", "single-slit", "central maxima", "diffraction"),
        2.0,
        3,
    ),
    (
        "ch11.photoelectric",
        "Photoelectric effect and Einstein's equation",
        11,
        ("photoelectric", "einstein's photoelectric", "work function", "stopping potential", "threshold frequency"),
        3.0,
        5,
    ),
    (
        "ch11.de_broglie",
        "de Broglie matter waves",
        11,
        ("de broglie", "de-broglie", "matter wave"),
        2.0,
        3,
    ),
    (
        "ch12.bohr",
        "Rutherford scattering and the Bohr model",
        12,
        ("bohr model", "bohr's model", "rutherford", "alpha-particle scattering", "alpha particle scattering"),
        3.0,
        5,
    ),
    (
        "ch12.spectra",
        "Hydrogen line spectra",
        12,
        ("line spectra", "spectral series", "balmer", "lyman"),
        1.5,
        2,
    ),
    (
        "ch13.binding",
        "Mass defect and binding energy",
        13,
        ("binding energy", "mass defect", "binding energy per nucleon"),
        2.5,
        3,
    ),
    (
        "ch13.fission_fusion",
        "Nuclear fission and fusion",
        13,
        ("nuclear fission", "nuclear fusion"),
        2.0,
        3,
    ),
    (
        "ch14.bands",
        "Energy bands and extrinsic semiconductors",
        14,
        ("energy bands", "intrinsic semiconductor", "extrinsic", "p-type", "n-type", "p type semiconductor"),
        2.0,
        3,
    ),
    (
        "ch14.diode",
        "p-n junction diode and rectifiers",
        14,
        ("p-n junction", "pn junction", "forward bias", "reverse bias", "full wave rectifier", "half wave rectifier", "junction diode"),
        2.5,
        3,
    ),
)


@dataclass(frozen=True)
class Taxonomy:
    concepts: tuple[Concept, ...]
    groups: tuple[UnitGroup, ...]

    @property
    def by_id(self) -> dict[str, Concept]:
        return {concept.id: concept for concept in self.concepts}

    def group(self, concept: Concept) -> UnitGroup:
        for item in self.groups:
            if item.id == concept.unit_group:
                return item
        raise KeyError(concept.unit_group)

    def concepts_in_group(self, group_id: str) -> tuple[Concept, ...]:
        return tuple(concept for concept in self.concepts if concept.unit_group == group_id)


def _build() -> Taxonomy:
    groups_by_chapter: dict[int, str] = {}
    for group in UNIT_GROUPS:
        for chapter in group.chapters:
            groups_by_chapter[chapter] = group.id
    concepts: list[Concept] = []
    for concept_id, name, chapter_number, keywords, hours, marks in _RAW:
        concepts.append(
            Concept(
                id=concept_id,
                name=name,
                chapter_number=chapter_number,
                chapter=CHAPTERS[chapter_number],
                unit_group=groups_by_chapter[chapter_number],
                keywords=tuple(keyword.casefold() for keyword in keywords),
                study_hours=hours,
                typical_marks=marks,
            )
        )
    taxonomy = Taxonomy(concepts=tuple(concepts), groups=UNIT_GROUPS)
    _validate(taxonomy)
    return taxonomy


def _validate(taxonomy: Taxonomy) -> None:
    ids = [concept.id for concept in taxonomy.concepts]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate concept id in taxonomy")
    if sum(group.marks for group in taxonomy.groups) != THEORY_MARKS:
        raise RuntimeError("unit-group marks must total the 70-mark theory paper")
    covered = tuple(chapter for group in taxonomy.groups for chapter in group.chapters)
    if tuple(sorted(covered)) != tuple(range(1, 15)):
        raise RuntimeError("taxonomy must cover chapters 1 through 14 exactly once")
    for concept in taxonomy.concepts:
        if not concept.keywords:
            raise RuntimeError(f"{concept.id} has no keywords")
        if concept.study_hours <= 0 or concept.typical_marks <= 0:
            raise RuntimeError(f"{concept.id} has a bad planning weight")


DEFAULT_TAXONOMY = _build()
