from rest_framework import permissions
from .models import OrdenItem


def _rol_usuario(user) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return 'administrador'
    perfil = getattr(user, 'perfil_ecommerce', None)
    return perfil.rol if perfil else 'cliente'


class EsAdminOVendedor(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return _rol_usuario(request.user) in {'administrador', 'vendedor'}


class PuedeVender(permissions.BasePermission):
    message = 'El usuario no tiene rol de vendedor o administrador habilitado.'

    def has_permission(self, request, view) -> bool:
        return _rol_usuario(request.user) in {'administrador', 'vendedor'}


class EsPropietarioOAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if _rol_usuario(request.user) == 'administrador':
            return True
        if hasattr(obj, 'usuario'):
            return obj.usuario == request.user
        if hasattr(obj, 'vendedor'):
            return obj.vendedor == request.user
        return obj == request.user


class EsCompradorVerificado(permissions.BasePermission):
    message = 'Solo clientes con compra verificada pueden registrar una reseña.'

    def has_permission(self, request, view) -> bool:
        if request.method != 'POST':
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        producto_id = request.data.get('producto')
        if not producto_id:
            return True
        return OrdenItem.objects.filter(
            orden__usuario=request.user,
            producto_id=producto_id,
            orden__estado__in=['pagada', 'enviada', 'entregada'],
        ).exists()