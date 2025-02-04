"""
Implementation of a submit specific HTTP service view.
"""

from redis import RedisError

from ichnaea.api.exceptions import (
    ParseError,
    ServiceUnavailable,
    UploadSuccess,
)
from ichnaea.api.views import BaseAPIView
from ichnaea.data.tasks import queue_reports


class BaseSubmitView(BaseAPIView):
    """Common base class for all submit related views."""

    error_on_invalidkey = False  #:
    view_type = 'submit'  #:

    #: :exc:`ichnaea.api.exceptions.UploadSuccess`
    success = UploadSuccess

    def __init__(self, request):
        super(BaseSubmitView, self).__init__(request)
        self.email, self.nickname = self.get_request_user_data()

    def decode_request_header(self, header_name):
        value = self.request.headers.get(header_name, None)
        if isinstance(value, str):  # pragma: no cover
            value = value.decode('utf-8', 'ignore')
        return value

    def get_request_user_data(self):
        email = self.decode_request_header('X-Email')
        nickname = self.decode_request_header('X-Nickname')
        return (email, nickname)

    def emit_upload_metrics(self, value, api_key):
        tags = None
        if api_key.should_log('submit'):
            tags = ['key:%s' % api_key.name]
        self.stats_client.incr('data.batch.upload', tags=tags)

    def preprocess(self):
        try:
            request_data, errors = self.preprocess_request()

            if not request_data:
                # don't allow completely empty submit request
                raise self.prepare_exception(ParseError())

        except ParseError:
            # capture JSON exceptions for submit calls
            self.raven_client.captureException()
            raise

        return request_data

    def submit(self, api_key):
        # may raise HTTP error
        request_data = self.preprocess()

        # data pipeline using new internal data format
        reports = request_data['items']
        batch_size = 50
        for i in range(0, len(reports), batch_size):
            batch = reports[i:i + batch_size]
            # insert reports, expire the task if it wasn't processed
            # after six hours to avoid queue overload
            queue_reports.apply_async(
                kwargs={
                    'api_key': api_key.valid_key,
                    'email': self.email,
                    'ip': self.request.client_addr,
                    'nickname': self.nickname,
                    'reports': batch,
                },
                expires=21600)

        self.emit_upload_metrics(len(reports), api_key)

    def view(self, api_key):
        """
        Execute the view code and return a response.
        """
        try:
            self.submit(api_key)
        except RedisError:
            raise ServiceUnavailable()

        return self.prepare_exception(self.success())
