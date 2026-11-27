from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

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


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion', 'imagen']


class CuponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cupon
        fields = '__all__'


class PerfilEcommerceSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='usuario.username', read_only=True)
    email = serializers.EmailField(source='usuario.email', read_only=True)

    class Meta:
        model = PerfilEcommerce
        fields = [
            'id',
            'usuario',
            'username',
            'email',
            'rol',
            'telefono',
            'direccion_predeterminada',
            'puntos_fidelidad',
        ]
        read_only_fields = ['id', 'usuario', 'puntos_fidelidad']


class ProductoSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='producto-detail')
    vendedor = serializers.HyperlinkedRelatedField(
        view_name='user-detail',
        read_only=True,
    )
    resenas_url = serializers.HyperlinkedIdentityField(
        view_name='producto-resenas',
        read_only=True,
    )
    categoria = CategoriaSerializer(read_only=True)
    categoria_id = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.all(),
        source='categoria',
        write_only=True,
    )
    precio_con_descuento = serializers.SerializerMethodField()
    rating_promedio = serializers.SerializerMethodField()
    disponible = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'url',
            'resenas_url',
            'id',
            'sku',
            'nombre',
            'descripcion',
            'marca',
            'categoria',
            'categoria_id',
            'vendedor',
            'precio',
            'descuento_porcentaje',
            'precio_con_descuento',
            'stock',
            'disponible',
            'rating_promedio',
            'imagenes',
            'especificaciones_tecnicas',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'vendedor', 'fecha_creacion']

    def get_precio_con_descuento(self, obj: Producto) -> str:
        return f'{obj.precio_con_descuento:.2f}'

    def get_rating_promedio(self, obj: Producto) -> float:
        return obj.rating_promedio

    def get_disponible(self, obj: Producto) -> bool:
        return obj.disponible

    def validate_precio(self, value: Decimal) -> Decimal:
        if value <= Decimal('0.00'):
            raise serializers.ValidationError('El precio debe ser mayor a 0.')
        return value


class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    precio_unitario = serializers.DecimalField(
        source='producto.precio_con_descuento',
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    subtotal_item = serializers.SerializerMethodField()

    class Meta:
        model = ItemCarrito
        fields = [
            'id',
            'producto',
            'producto_sku',
            'producto_nombre',
            'precio_unitario',
            'cantidad',
            'subtotal_item',
        ]
        read_only_fields = ['id']

    def get_subtotal_item(self, obj: ItemCarrito) -> str:
        monto = obj.producto.precio_con_descuento * Decimal(obj.cantidad)
        return f'{monto:.2f}'

    def validate(self, attrs):
        producto = attrs.get('producto', getattr(self.instance, 'producto', None))
        cantidad = attrs.get('cantidad', getattr(self.instance, 'cantidad', 1))
        if producto and cantidad > producto.stock:
            raise serializers.ValidationError(
                {'cantidad': f'Stock insuficiente. Disponible: {producto.stock} unidades.'}
            )
        return attrs


class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)
    cupon_codigo = serializers.CharField(source='cupon.codigo', read_only=True, default=None)
    subtotal = serializers.SerializerMethodField()
    impuestos = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    total_con_descuento = serializers.SerializerMethodField()
    cantidad_items = serializers.SerializerMethodField()

    class Meta:
        model = Carrito
        fields = [
            'id',
            'usuario',
            'activo',
            'cupon',
            'cupon_codigo',
            'items',
            'cantidad_items',
            'subtotal',
            'impuestos',
            'total',
            'total_con_descuento',
            'actualizado_en',
        ]
        read_only_fields = ['id', 'usuario', 'actualizado_en']

    def get_subtotal(self, obj: Carrito) -> str:
        return f'{obj.subtotal:.2f}'

    def get_impuestos(self, obj: Carrito) -> str:
        return f'{obj.impuestos:.2f}'

    def get_total(self, obj: Carrito) -> str:
        return f'{obj.total:.2f}'

    def get_total_con_descuento(self, obj: Carrito) -> str:
        return f'{obj.total_con_descuento:.2f}'

    def get_cantidad_items(self, obj: Carrito) -> int:
        return obj.cantidad_items

    def validate(self, attrs):
        request = self.context.get('request')
        activo = attrs.get('activo', True)
        if request and request.user.is_authenticated and activo and self.instance is None:
            existe_activo = Carrito.objects.filter(usuario=request.user, activo=True).exists()
            if existe_activo:
                raise serializers.ValidationError(
                    {'activo': 'El usuario ya cuenta con un carrito activo.'}
                )
        return attrs


class OrdenItemSnapshotSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrdenItem
        fields = [
            'id',
            'producto',
            'producto_sku',
            'producto_nombre',
            'cantidad',
            'precio_unitario',
            'subtotal',
        ]
        read_only_fields = fields

    def get_subtotal(self, obj: OrdenItem) -> str:
        return f'{(obj.precio_unitario * Decimal(obj.cantidad)):.2f}'


class OrdenSerializer(serializers.ModelSerializer):
    items = OrdenItemSnapshotSerializer(many=True, read_only=True)
    tiempo_estimado_entrega = serializers.SerializerMethodField()

    class Meta:
        model = Orden
        fields = [
            'id',
            'usuario',
            'items',
            'direccion_envio',
            'metodo_pago',
            'estado',
            'total',
            'numero_seguimiento',
            'tiempo_estimado_entrega',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'usuario', 'total', 'numero_seguimiento', 'fecha_creacion']

    def get_tiempo_estimado_entrega(self, obj: Orden) -> dict:
        return obj.tiempo_estimado_entrega

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        usuario = request.user
        carrito = (
            Carrito.objects.prefetch_related('items__producto')
            .filter(usuario=usuario, activo=True)
            .first()
        )
        if not carrito or not carrito.items.exists():
            raise serializers.ValidationError(
                'No tienes un carrito activo con productos para generar la orden.'
            )

        for item in carrito.items.all():
            if item.cantidad > item.producto.stock:
                raise serializers.ValidationError(
                    f'Sin stock suficiente para {item.producto.nombre} (disponible: {item.producto.stock}).'
                )

        orden = Orden.objects.create(
            usuario=usuario,
            direccion_envio=validated_data['direccion_envio'],
            metodo_pago=validated_data['metodo_pago'],
            estado='pendiente',
            total=carrito.total_con_descuento,
        )

        for item in carrito.items.all():
            precio_compra = item.producto.precio_con_descuento
            OrdenItem.objects.create(
                orden=orden,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=precio_compra,
            )
            item.producto.stock -= item.cantidad
            item.producto.save(update_fields=['stock'])

        carrito.items.all().delete()
        carrito.activo = False
        carrito.save(update_fields=['activo', 'actualizado_en'])
        return orden


class ResenaSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    es_compra_verificada = serializers.SerializerMethodField()

    class Meta:
        model = Resena
        fields = [
            'id',
            'usuario',
            'usuario_username',
            'producto',
            'calificacion',
            'titulo',
            'comentario',
            'es_compra_verificada',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'usuario', 'es_compra_verificada', 'fecha_creacion']

    def get_es_compra_verificada(self, obj: Resena) -> bool:
        return obj.es_compra_verificada

    def validate_calificacion(self, value: int) -> int:
        if not 1 <= value <= 5:
            raise serializers.ValidationError('La calificación debe estar entre 1 y 5.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        producto = attrs.get('producto', getattr(self.instance, 'producto', None))
        if request and request.user.is_authenticated and producto:
            compro = OrdenItem.objects.filter(
                orden__usuario=request.user,
                producto=producto,
                orden__estado__in=['pagada', 'enviada', 'entregada'],
            ).exists()
            if not compro:
                raise serializers.ValidationError(
                    {'producto': 'Solo puedes reseñar productos que hayas comprado.'}
                )
        return attrs