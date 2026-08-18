# SPDX-License-Identifier: MIT
# See LICENSE file in the repository root for full license text.
import io

from django.utils.deprecation import MiddlewareMixin


class BufferRequestMiddleware(MiddlewareMixin):
    """
    Reads request.body once and caches it so that subsequent reads
    throughout the request/response cycle return the same data.
    This is transparent to the rest of the application.
    """

    def process_request(self, request):
        # 1. Force read the body to cache it in request._body
        body = request.body
        # 2. Replace the stream with a fresh BytesIO for safety
        request._stream = io.BytesIO(body)

        # Accessing request.body reads the raw stream and stores the result
        # on the request object, making it available for repeated reads.
        # _ = request.body

        # Reset the stream position so any code that reads _stream directly
        # also starts from the beginning.
        # if request._stream and hasattr(request._stream, "seek"):
        #    request._stream.seek(0)
        return None
