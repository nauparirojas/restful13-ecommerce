from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination


class ProductoPageNumberPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrdenLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 50
    max_limit = 200