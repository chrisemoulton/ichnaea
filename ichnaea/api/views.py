"""
Implementation of a API specific HTTP service view.
"""

import colander
import simplejson as json
import six

from ichnaea.api.exceptions import (
    DailyLimitExceeded,
    InvalidAPIKey,
    ParseError,
)
from ichnaea.api.rate_limit import rate_limit_exceeded
from ichnaea.models.api import ApiKey
from ichnaea import util
from ichnaea.webapp.view import BaseView

if six.PY2:  # pragma: no cover
    from ipaddr import IPAddress as ip_address  # NOQA
else:  # pragma: no cover
    from ipaddress import ip_address


class BaseAPIView(BaseView):
    """Common base class for all API related views."""

    check_api_key = True  #: Should API keys be checked?
    error_on_invalidkey = True  #: Deny access for invalid API keys?
    metric_path = None  #: Dotted URL path, for example v1.submit.
    schema = None  #: An instance of a colander schema to validate the data.
    view_type = None  #: The type of view, for example submit or locate.

    def __init__(self, request):
        super(BaseAPIView, self).__init__(request)
        self.raven_client = request.registry.raven_client
        self.redis_client = request.registry.redis_client
        self.stats_client = request.registry.stats_client

    def log_unique_ip(self, apikey_shortname):
        try:
            ip = str(ip_address(self.request.client_addr))
        except ValueError:  # pragma: no cover
            ip = None
        if ip:
            redis_key = 'apiuser:{api_type}:{api_name}:{date}'.format(
                api_type=self.view_type,
                api_name=apikey_shortname,
                date=util.utcnow().date().strftime('%Y-%m-%d'),
            )
            with self.redis_client.pipeline() as pipe:
                pipe.pfadd(redis_key, ip)
                pipe.expire(redis_key, 691200)  # 8 days
                pipe.execute()

    def log_count(self, apikey_shortname, should_log):
        self.stats_client.incr(
            self.view_type + '.request',
            tags=['path:' + self.metric_path,
                  'key:' + apikey_shortname])

        if self.request.client_addr and should_log:
            try:
                self.log_unique_ip(apikey_shortname)
            except Exception:  # pragma: no cover
                self.raven_client.captureException()

    def check(self):
        api_key = None
        api_key_text = self.request.GET.get('key', None)
        skip_check = False

        if api_key_text is None:
            self.log_count('none', False)
            if self.error_on_invalidkey:
                raise self.prepare_exception(InvalidAPIKey())

        if api_key_text is not None:
            try:
                session = self.request.db_ro_session
                api_key = session.query(ApiKey).get(api_key_text)
            except Exception:
                # if we cannot connect to backend DB, skip api key check
                skip_check = True
                self.raven_client.captureException()

        if api_key is not None:
            self.log_count(api_key.name, api_key.should_log(self.view_type))

            rate_key = 'apilimit:{key}:{path}:{time}'.format(
                key=api_key_text,
                path=self.metric_path,
                time=util.utcnow().strftime('%Y%m%d')
            )

            should_limit = rate_limit_exceeded(
                self.redis_client,
                rate_key,
                maxreq=api_key.maxreq
            )

            if should_limit:
                raise self.prepare_exception(DailyLimitExceeded())
        elif skip_check:
            pass
        else:
            if api_key_text is not None:
                self.log_count('invalid', False)
            if self.error_on_invalidkey:
                raise self.prepare_exception(InvalidAPIKey())

        # If we failed to look up an ApiKey, create an empty one
        # rather than passing None through
        api_key = api_key or ApiKey(valid_key=None)
        return self.view(api_key)

    def preprocess_request(self):
        errors = []

        request_content = self.request.body
        if self.request.headers.get('Content-Encoding') == 'gzip':
            # handle gzip self.request bodies
            try:
                request_content = util.decode_gzip(self.request.body)
            except OSError as exc:
                errors.append({'name': None, 'description': repr(exc)})

        request_data = {}
        try:
            request_data = json.loads(
                request_content, encoding=self.request.charset)
        except ValueError as exc:
            errors.append({'name': None, 'description': repr(exc)})

        validated_data = {}
        try:
            validated_data = self.schema.deserialize(request_data)
        except colander.Invalid as exc:
            errors.append({'name': None, 'description': exc.asdict()})

        if request_content and errors:
            raise self.prepare_exception(ParseError())

        return (validated_data, errors)

    def __call__(self):
        """Execute the view and return a response."""
        if self.check_api_key:
            return self.check()
        else:
            api_key = ApiKey(
                valid_key=None, allow_fallback=False,
                log_locate=False, log_region=False, log_submit=False)
            return self.view(api_key)
