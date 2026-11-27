from django.db import transaction
from django.contrib.auth import get_user_model

User = get_user_model()
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Carrito,
    Categoria,
    Cupon,
    ItemCarrito,
    Orden,
    OrdenItem,
    PerfilEcommerce,
    Producto,
    Resena,
)
from .serializers import (
    CarritoSerializer,
    CategoriaSerializer,
    CuponSerializer,
    OrdenSerializer,
    PerfilEcommerceSerializer,
    ProductoSerializer,
    ResenaSerializer,
)


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    @action(detail=True, methods=['get'])
    def resenas(self, request, pk=None):
        producto = self.get_object()
        queryset = Resena.objects.filter(producto=producto).select_related('usuario')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ResenaSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ResenaSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

class ResenaViewSet(viewsets.ModelViewSet):
    queryset = Resena.objects.select_related("usuario", "producto").all()
    serializer_class = ResenaSerializer


class CuponViewSet(viewsets.ModelViewSet):
    queryset = Cupon.objects.all()
    serializer_class = CuponSerializer


class CarritoViewSet(viewsets.ModelViewSet):
    queryset = Carrito.objects.none()
    serializer_class = CarritoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Carrito.objects.none()
        return Carrito.objects.filter(usuario=self.request.user).prefetch_related("items__producto")


class OrdenViewSet(viewsets.ModelViewSet):
    queryset = Orden.objects.none()
    serializer_class = OrdenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return Orden.objects.none()
        user = self.request.user
        if user.is_staff:
            return Orden.objects.select_related("usuario").prefetch_related("items__producto").all()
        return Orden.objects.select_related("usuario").prefetch_related("items__producto").filter(usuario=user)


class PerfilEcommerceViewSet(viewsets.ModelViewSet):
    queryset = PerfilEcommerce.objects.none()
    serializer_class = PerfilEcommerceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return PerfilEcommerce.objects.none()
        if self.request.user.is_staff:
            return PerfilEcommerce.objects.select_related("usuario").all()
        return PerfilEcommerce.objects.select_related("usuario").filter(usuario=self.request.user)


class _UsuarioPublicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class UsuarioReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = _UsuarioPublicoSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]