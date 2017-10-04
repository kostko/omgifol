import tatsu

from .wadio import WadIO

__all__ = [
    'UDMFMapEditor',
]

# UDMF grammar.
UDMF_GRAMMAR = r'''
    @@grammar::UDMF
    @@comments :: /\\\*.*?\*\//
    @@eol_comments :: /\/\/.*?$/

    translation_unit = global_expr_list $ ;

    global_expr_list = { global_expr } ;

    global_expr = block | assignment_expr ;

    block = identifier '{' ~ expr_list '}' ;

    expr_list = { assignment_expr } ;

    assignment_expr = identifier '=' value ';' ;

    identifier = /[A-Za-z_]+[A-Za-z0-9_]*/ ;

    value = float | integer | quoted_string | boolean | keyword ;

    integer = '0' | /[+-]?[1-9]+[0-9]*/ | /0[0-9]+/ | /0x[0-9A-Fa-f]+/ ;

    float = /[+-]?[0-9]+\.[0-9]*([eE][+-]?[0-9]+)?/ ;

    boolean = 'true' | 'false' ;

    quoted_string = /"([^"\\]*(\\.[^"\\]*)*)"/ ;

    keyword = /[^{}();"'\n\t ]+/ ;
'''

# Compiled UDMF parser.
UDMF_PARSER = tatsu.compile(UDMF_GRAMMAR)


class UDMFObject(object):
    """Generic UDMF object."""

    def __init__(self, attributes, name=None):
        self.name = name
        self._attributes = []
        for key, value in attributes.items():
            self._attributes.append(key)
            setattr(self, key, value)

    def serialize(self):
        """Serialize current UDMF object."""
        return '{name}\n{{\n{attributes}\n}}\n'.format(
            name=self.name,
            attributes='\n'.join([
                self.serialize_assignment(key, getattr(self, key))
                for key in self._attributes
            ])
        )

    @classmethod
    def serialize_assignment(cls, key, value):
        """Serialize assignment expression."""
        if isinstance(value, str):
            value = '"{}"'.format(value)
        elif isinstance(value, bool):
            value = 'true' if value else 'false'

        return '{} = {};'.format(key, value)

    def __repr__(self):
        return '<{} name={} attributes={}>'.format(
            self.__class__.__name__,
            self.name,
            {key: getattr(self, key) for key in self._attributes}
        )


class Thing(UDMFObject):
    pass


class Vertex(UDMFObject):
    pass


class LineDef(UDMFObject):
    pass


class SideDef(UDMFObject):
    pass


class Sector(UDMFObject):
    pass


class UDMFSemantics(object):
    # UDMF block types.
    UDMF_BLOCK_TYPES = {
        'thing': Thing,
        'vertex': Vertex,
        'linedef': LineDef,
        'sidedef': SideDef,
        'sector': Sector,
    }

    def block(self, ast):
        name, _, assignments, _ = ast

        result = {}
        for assignment in assignments:
            result.update(assignment)

        return self.UDMF_BLOCK_TYPES.get(name, UDMFObject)(result, name=name)

    def assignment_expr(self, ast):
        identifier, _, value, _ = ast
        return {identifier: value}

    def keyword(self, ast):
        raise NotImplementedError("Unsupported keyword: {}".format(repr(ast)))

    def quoted_string(self, ast):
        return ast[1:-1]

    def integer(self, ast):
        return int(ast)

    def float(self, ast):
        return float(ast)

    def boolean(self, ast):
        return bool(ast)


class UDMFMapEditor(object):
    """Simple UDMF map editor."""

    def __init__(self, wadio):
        self.name = None
        self.data = None
        self.index = None

        # Read WAD file into memory so we don't need WadIO anymore.
        self._wad_entries = list(wadio.entries)
        self._wad_data = [wadio.read(index) for index in range(len(wadio.entries))]

        self._nodes = []
        self._meta = {}

    def load(self, name):
        """Load lumps from the WAD file."""
        for index, entry in enumerate(self._wad_entries):
            try:
                # Assume current lump is a header lump. The next lump should be a TEXTMAP.
                next_entry = self._wad_entries[index + 1]
                if next_entry.name != 'TEXTMAP':
                    continue
            except IndexError:
                # No UDMF map found.
                break

            # Found UDMF map. Scan until the ENDMAP marker.
            if entry.name != name:
                continue

            self.name = entry.name
            self.index = index

            for subindex, entry in enumerate(self._wad_entries[index:]):
                if entry.name == 'ENDMAP':
                    break
                elif entry.name == 'TEXTMAP':
                    self.data = self._wad_data[index + subindex].decode('ascii')
                else:
                    # Ignore unknown lumps.
                    pass

            # Edit only a single map at a time.
            break

        # Sanity check if any map was found.
        if not self.name or not self.data:
            raise IOError("Unable to find an UDMF map")

        self._parse()

    def _parse(self):
        """Parse UDMF map format."""
        ast = UDMF_PARSER.parse(self.data, semantics=UDMFSemantics())

        for node in ast:
            if isinstance(node, UDMFObject):
                self._nodes.append(node)
            elif isinstance(node, dict):
                self._meta.update(node)

    def serialize(self):
        """Serialize map into UDMF format."""
        meta = '\n'.join([UDMFObject.serialize_assignment(key, value) for key, value in self._meta.items()])
        nodes = '\n'.join([node.serialize() for node in self._nodes])
        return '\n'.join([meta, nodes])

    def save(self, filename):
        """Save map to an output WAD file."""
        output = WadIO(filename)
        for index, entry in enumerate(self._wad_entries):
            if index == self.index + 1:
                # Replace map at specified index.
                data = self.serialize().encode('ascii')
            else:
                # Copy all other entries (even other maps).
                data = self._wad_data[index]

            output.insert(entry.name, data)

        output.save()
        output.close()

    def get_nodes(self, type):
        """Return nodes of specific type."""
        return [node for node in self._nodes if isinstance(node, type)]

    @property
    def sectors(self):
        """A list of map sectors."""
        return self.get_nodes(Sector)

    @property
    def sidedefs(self):
        """A list of map side defs."""
        return self.get_nodes(SideDef)

    @property
    def linedefs(self):
        """A list of map line defs."""
        return self.get_nodes(LineDef)

    @property
    def vertices(self):
        """A list of map vertices."""
        return self.get_nodes(Vertex)

    @property
    def things(self):
        """A list of map things."""
        return self.get_nodes(Thing)
