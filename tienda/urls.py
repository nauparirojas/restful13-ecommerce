from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    CarritoViewSet,
    OrdenViewSet,
    ProductoViewSet,
    ResenaViewSet,
    UsuarioReadOnlyViewSet,
)

router = DefaultRouter()
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'carrito', CarritoViewSet, basename='carrito')
router.register(r'ordenes', OrdenViewSet, basename='orden')
router.register(r'resenas', ResenaViewSet, basename='resena')
router.register(r'usuarios', UsuarioReadOnlyViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]