# matches the schema definition of:
# https://developers.google.com/maps/documentation/business/geolocation/

import colander

from ichnaea.api.schema import (
    InternalMappingSchema,
    InternalSchemaNode,
    InternalSequenceSchema,
)
from ichnaea.api.locate.schema import (
    BaseLocateSchema,
    FallbackSchema,
)

RADIO_STRINGS = ['gsm', 'cdma', 'wcdma', 'lte']


class CellTowersSchema(InternalSequenceSchema):

    @colander.instantiate()
    class SequenceItem(InternalMappingSchema):

        # radio is a FxOS specific undocumented workaround
        radio = InternalSchemaNode(
            colander.String(),
            validator=colander.OneOf(RADIO_STRINGS), missing=colander.drop)
        # radioType resolves to the internal field 'radio', so if both
        # 'radio' and 'radioType' are provided, radioType should take
        # precedence. colander respects the order that fields are defined
        # and so radioType is defined after the 'radio' field.
        radioType = InternalSchemaNode(
            colander.String(), validator=colander.OneOf(RADIO_STRINGS),
            missing=colander.drop, internal_name='radio')
        mobileCountryCode = InternalSchemaNode(
            colander.Integer(), missing=None, internal_name='mcc')
        mobileNetworkCode = InternalSchemaNode(
            colander.Integer(), missing=None, internal_name='mnc')
        locationAreaCode = InternalSchemaNode(
            colander.Integer(), missing=None, internal_name='lac')
        cellId = InternalSchemaNode(
            colander.Integer(), missing=None, internal_name='cid')

        age = InternalSchemaNode(colander.Integer(), missing=None)
        psc = InternalSchemaNode(colander.Integer(), missing=None)
        signalStrength = InternalSchemaNode(
            colander.Integer(), missing=None, internal_name='signal')
        timingAdvance = InternalSchemaNode(
            colander.Integer(), missing=None, internal_name='ta')


class WifiAccessPointsSchema(InternalSequenceSchema):

    @colander.instantiate()
    class SequenceItem(InternalMappingSchema):

        macAddress = InternalSchemaNode(
            colander.String(), missing=None, internal_name='mac')
        age = InternalSchemaNode(colander.Integer(), missing=None)
        channel = InternalSchemaNode(colander.Integer(), missing=None)
        frequency = InternalSchemaNode(colander.Integer(), missing=None)
        signalStrength = InternalSchemaNode(
            colander.Integer(), missing=None, internal_name='signal')
        signalToNoiseRatio = InternalSchemaNode(
            colander.Integer(), missing=None, internal_name='snr')
        ssid = InternalSchemaNode(colander.String(), missing=None)


class LocateV2Schema(BaseLocateSchema):

    carrier = InternalSchemaNode(colander.String(), missing=None)
    considerIp = InternalSchemaNode(colander.Boolean(), missing=True)
    homeMobileCountryCode = InternalSchemaNode(
        colander.Integer(), missing=None)
    homeMobileNetworkCode = InternalSchemaNode(
        colander.Integer(), missing=None)
    radioType = InternalSchemaNode(
        colander.String(), validator=colander.OneOf(RADIO_STRINGS),
        missing=colander.drop, internal_name='radio')

    cellTowers = CellTowersSchema(missing=(), internal_name='cell')
    wifiAccessPoints = WifiAccessPointsSchema(missing=(), internal_name='wifi')
    fallbacks = FallbackSchema(missing=None)

    def __init__(self, *args, **kw):
        super(LocateV2Schema, self).__init__(*args, **kw)
        self.fallback_defaults = self.get('fallbacks').deserialize({})

    def deserialize(self, data):
        data = super(LocateV2Schema, self).deserialize(data)
        if data['fallbacks'] is None:
            data['fallbacks'] = dict(self.fallback_defaults)
            data['fallbacks']['ipf'] = data['considerIp']
        return data

LOCATE_V2_SCHEMA = LocateV2Schema()
