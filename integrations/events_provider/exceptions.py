class EventsProviderError(Exception):
    pass


class ProviderAuthError(EventsProviderError):
    pass


class ProviderTemporaryError(EventsProviderError):
    pass


class ProviderRateLimitError(EventsProviderError):
    pass


class ProviderNotFoundError(EventsProviderError):
    pass


class ProviderBadResponseError(EventsProviderError):
    pass


class ProviderBusinessError(EventsProviderError):
    pass
