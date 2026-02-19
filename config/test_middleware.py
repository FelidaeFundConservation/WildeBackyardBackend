from django.test import RequestFactory, TestCase

from config.middleware import BufferRequestMiddleware


class BufferRequestMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = BufferRequestMiddleware(get_response=lambda r: None)

    def test_body_is_readable_multiple_times(self):
        """request.body must return the same bytes on repeated accesses."""
        payload = b'{"key": "value"}'
        request = self.factory.post(
            "/api/test/",
            data=payload,
            content_type="application/json",
        )
        self.middleware.process_request(request)

        first_read = request.body
        second_read = request.body
        self.assertEqual(first_read, payload)
        self.assertEqual(first_read, second_read)

    def test_stream_is_seeked_to_start(self):
        """After caching, request._stream must be positioned at the start."""
        payload = b'{"key": "value"}'
        request = self.factory.post(
            "/api/test/",
            data=payload,
            content_type="application/json",
        )
        self.middleware.process_request(request)

        # After body is cached Django sets _stream to a BytesIO of the body.
        # Our middleware must seek it back to position 0.
        if request._stream and hasattr(request._stream, "tell"):
            self.assertEqual(request._stream.tell(), 0)

    def test_empty_body_does_not_raise(self):
        """Middleware must handle requests with no body gracefully."""
        request = self.factory.get("/api/test/")
        # Should not raise any exception
        self.middleware.process_request(request)
        self.assertEqual(request.body, b"")
