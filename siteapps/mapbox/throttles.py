from rest_framework.throttling import SimpleRateThrottle


class SearchSuggestionsPerMinuteThrottle(SimpleRateThrottle):
    scope = "search_suggestions_per_minute"
    rate = "50/min"


class GeocodePerMinuteThrottle(SimpleRateThrottle):
    scope = "geocode_per_minute"
    rate = "5/min"


class SearchSuggestionsPerDayThrottle(SimpleRateThrottle):
    scope = "search_suggestions_per_day"
    rate = "250/day"


class GeocodePerDayThrottle(SimpleRateThrottle):
    scope = "geocode_per_day"
    rate = "50/day"
