from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle


class CatalogoAnonRateThrottle(AnonRateThrottle):
    scope = 'anon'


class EcommerceUserRateThrottle(UserRateThrottle):
    scope = 'user'


class CheckoutRateThrottle(ScopedRateThrottle):
    scope = 'checkout'


class SearchRateThrottle(ScopedRateThrottle):
    scope = 'search'