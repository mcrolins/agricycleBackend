from django.utils.cache import add_never_cache_headers


class NoCacheAuthenticatedApiMiddleware:
    """
    Prevent browsers from reusing stale authenticated API responses from history/cache.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith("/api/"):
            add_never_cache_headers(response)
            response["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response
