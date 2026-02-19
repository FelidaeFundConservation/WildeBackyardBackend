from django.utils.deprecation import MiddlewareMixin


class BufferRequestMiddleware(MiddlewareMixin):
    """
    Reads request.body once and caches it so that subsequent reads
    throughout the request/response cycle return the same data.
    This is transparent to the rest of the application.
    """

    def process_request(self, request):
        # Accessing request.body reads the raw stream and stores the result
        # on the request object, making it available for repeated reads.
        _ = request.body

        # Reset the stream position so any code that reads _stream directly
        # also starts from the beginning.
        if request._stream and hasattr(request._stream, "seek"):
            request._stream.seek(0)
