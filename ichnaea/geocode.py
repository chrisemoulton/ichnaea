"""
Contains helper functions for region related tasks.
"""

from collections import namedtuple
import os

import genc
import mobile_codes
from shapely import geometry
from shapely import prepared
import simplejson
from rtree import index

from ichnaea import geocalc
from ichnaea import util

JSON_FILE = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), 'regions.geojson.gz')

DATELINE_EAST = geometry.box(180.0, -90.0, 270.0, 90.0)
DATELINE_WEST = geometry.box(-270.0, -90.0, -180.0, 90.0)

# Palestine only exists as West Bank/Gaza in the GENC dataset
MCC_GENC_SHAPEFILE_MAP = {
    'PS': 'XW',
}

Region = namedtuple('Region', 'code name radius')


class Geocoder(object):
    """
    The Geocoder offers reverse geocoding lat/lon positions
    into region codes.
    """

    _buffered_shapes = None  #: maps region code to a buffered prepared shape
    _prepared_shapes = None  #: maps region code to a precise prepared shape
    _shapes = None  #: maps region code to a precise shape
    _tree = None  #: RTree of buffered region envelopes
    _tree_ids = None  #: maps RTree entry id to region code
    _valid_regions = None  #: Set of known and valid region codes
    _radii = None  #: A cache of region radii

    def __init__(self, json_file=JSON_FILE):
        self._buffered_shapes = {}
        self._prepared_shapes = {}
        self._shapes = {}
        self._tree_ids = {}
        self._radii = {}

        with util.gzip_open(json_file, 'r') as fd:
            data = simplejson.load(fd)

        genc_regions = frozenset([rec.alpha2 for rec in genc.REGIONS])
        for feature in data['features']:
            code = feature['properties']['alpha2']
            if code in genc_regions:
                shape = geometry.shape(feature['geometry'])
                self._shapes[code] = shape
                self._prepared_shapes[code] = prepared.prep(shape)
                self._radii[code] = feature['properties']['radius']

        i = 0
        envelopes = []
        for code, shape in self._shapes.items():
            # Build up region buffers, to create shapes that include all of
            # the coastal areas and boundaries of the regions and anywhere
            # a cell signal could still be recorded. The value is in decimal
            # degrees (1.0 == ~100km) but calculations don't take projection
            # / WSG84 into account.
            # After buffering remove any parts that crosses the -180.0/+180.0
            # longitude boundary to the east or west.
            buffered = (shape.buffer(0.5)
                             .difference(DATELINE_EAST)
                             .difference(DATELINE_WEST))
            self._buffered_shapes[code] = prepared.prep(buffered)

            # Collect rtree index entries, and maintain a separate id to
            # code mapping. We don't use index object support as it
            # requires un/pickling the object entries on each lookup.
            if isinstance(buffered, geometry.base.BaseMultipartGeometry):
                # Index bounding box of individual polygons instead of
                # the multipolygon, to avoid issues with regions crossing
                # the -180.0/+180.0 longitude boundary.
                for geom in buffered.geoms:
                    envelopes.append((i, geom.envelope.bounds, None))
                    self._tree_ids[i] = code
                    i += 1
            else:
                envelopes.append((i, buffered.envelope.bounds, None))
                self._tree_ids[i] = code
                i += 1

        props = index.Property()
        props.fill_factor = 0.9
        props.leaf_capacity = 20
        self._tree = index.Index(envelopes, interleaved=True, properties=props)
        self._valid_regions = frozenset(self._shapes.keys())

    @property
    def valid_regions(self):
        return self._valid_regions

    def region(self, lat, lon):
        """
        Return a region code matching the provided position.
        If the position is not found inside any region return None.
        """
        # Look up point in RTree of buffered region envelopes.
        # This is a coarse-grained but very fast match.
        point = geometry.Point(lon, lat)
        codes = [self._tree_ids[id_] for id_ in
                 self._tree.intersection(point.bounds)]

        if not codes:
            return None

        # match point against the buffered polygon shapes
        buffered_codes = [code for code in codes
                          if self._buffered_shapes[code].contains(point)]
        if len(buffered_codes) < 2:
            return buffered_codes[0] if buffered_codes else None

        # match point against the precise polygon shapes
        precise_codes = [code for code in buffered_codes
                         if self._prepared_shapes[code].contains(point)]

        if len(precise_codes) == 1:
            return precise_codes[0]

        # Use distance from the border of each region as the tie-breaker.
        distances = {}

        # point wasn't in any precise region, which one of the buffered
        # regions is it closest to?
        if not precise_codes:
            for code in buffered_codes:
                coords = []
                if isinstance(self._shapes[code].boundary,
                              geometry.base.BaseMultipartGeometry):
                    for geom in self._shapes[code].boundary.geoms:
                        coords.extend([coord for coord in geom.coords])
                else:
                    coords = self._shapes[code].boundary.coords
                for coord in coords:
                    distances[geocalc.distance(
                        coord[1], coord[0], lat, lon)] = code
            return distances[min(distances.keys())]

        # point was in multiple overlapping regions, take the one where it
        # is farthest away from the border / the most inside a region
        for code in precise_codes:
            coords = []
            if isinstance(self._shapes[code].boundary,
                          geometry.base.BaseMultipartGeometry):
                for geom in self._shapes[code].boundary.geoms:
                    coords.extend([coord for coord in geom.coords])
            else:
                coords = self._shapes[code].boundary.coords
            for coord in coords:
                distances[geocalc.distance(
                    coord[1], coord[0], lat, lon)] = code
        return distances[max(distances.keys())]

    def any_region(self, lat, lon):
        """
        Is the provided lat/lon position inside any of the regions?

        Returns False if the position is outside of all known regions.
        """
        point = geometry.Point(lon, lat)
        codes = [self._tree_ids[id_] for id_ in
                 self._tree.intersection(point.bounds)]

        for code in codes:
            if self._buffered_shapes[code].contains(point):
                return True

        return False

    def in_region(self, lat, lon, code):
        """
        Is the provided lat/lon position inside the region associated
        with the given region code.
        """
        if code not in self._valid_regions:
            return False

        point = geometry.Point(lon, lat)
        if self._buffered_shapes[code].contains(point):
            return True
        return False

    def in_region_mcc(self, lat, lon, mcc):
        """
        Is the provided lat/lon position inside one of the regions
        associated with the given mcc.
        """
        for code in self.regions_for_mcc(mcc):
            if self.in_region(lat, lon, code):
                return True
        return False

    def regions_for_mcc(self, mcc, metadata=False):
        """
        Return a list of region codes matching the passed in
        mobile country code.

        If the metadata argument is set to True, returns a list of
        dictionaries containing additional metadata instead.

        The return list is filtered by the set of recognized
        region codes present in the GENC dataset.
        """
        codes = [region.alpha2 for region in mobile_codes.mcc(str(mcc))]
        # map mcc region codes to genc region codes
        codes = [MCC_GENC_SHAPEFILE_MAP.get(code, code) for code in codes]
        valid_codes = set(codes).intersection(self._valid_regions)
        if not metadata:
            return list(valid_codes)

        result = []
        for code in valid_codes:
            region = genc.region_by_alpha2(code)
            if region is not None:
                result.append(Region(
                    code=region.alpha2,
                    name=region.name,
                    radius=self.region_max_radius(code)))
        return result

    def region_for_cell(self, lat, lon, mcc):
        """
        Return a region code matching the provided mcc and position.
        If the position is not found inside any region return None.
        """
        regions = []
        for code in self.regions_for_mcc(mcc):
            if self.in_region(lat, lon, code):
                regions.append(code)

        if not regions:
            return None
        if len(regions) == 1:
            return regions[0]

        # fall back to lookup without the mcc/region code hint
        return self.region(lat, lon)

    def region_max_radius(self, code):
        """
        Return the maximum radius of a circle encompassing the largest
        region subunit in meters, rounded to 1 km increments.
        """
        return self._radii.get(code, None)


GEOCODER = Geocoder()
