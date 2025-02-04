"""Implementation of a GeoIP based search source."""

from ichnaea.api.locate.constants import DataSource
from ichnaea.api.locate.source import (
    PositionSource,
    RegionSource,
    Source,
)


class GeoIPSource(Source):
    """A GeoIPSource returns search results based on a GeoIP database."""

    fallback_field = 'ipf'
    source = DataSource.geoip
    geoip_accuracy_field = 'radius'

    def search(self, query):
        result = self.result_type()
        source_used = False

        if query.ip:
            source_used = True

        # The GeoIP record is already available on the query object,
        # there's no need to do a lookup again.
        geoip = query.geoip
        if geoip:
            result = self.result_type(
                lat=geoip['latitude'],
                lon=geoip['longitude'],
                accuracy=geoip[self.geoip_accuracy_field],
                region_code=geoip['region_code'],
                region_name=geoip['region_name'],
                score=geoip['score'],
            )

        if source_used:
            query.emit_source_stats(self.source, result)

        return result


class GeoIPPositionSource(GeoIPSource, PositionSource):
    """A GeoIPSource returning position results."""


class GeoIPRegionSource(GeoIPSource, RegionSource):
    """A GeoIPSource returning region results."""

    geoip_accuracy_field = 'region_radius'
