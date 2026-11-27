import uuid
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.utils import timezone


class PerfilEcommerce(models.Model):
    ROL_CHOICES = [
        ('administrador', 'Administrador'),
        ('vendedor', 'Vendedor'),
        ('cliente', 'Cliente'),
        ('externo', 'Sistema Externo'),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_ecommerce',
    )
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='cliente')
    telefono = models.CharField(max_length=25, blank=True)
    direccion_predeterminada = models.TextField(blank=True)
    puntos_fidelidad = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Perfil E-commerce'
        verbose_name_plural = 'Perfiles E-commerce'

    def __str__(self) -> str:
        return f'{self.usuario.username} ({self.rol})'


class Categoria(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    imagen = models.URLField(blank=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self) -> str:
        return self.nombre


class Cupon(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    descuento_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('90.00'))],
    )
    activo = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f'{self.codigo} ({self.descuento_porcentaje}%)'


class Producto(models.Model):
    sku = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=200, db_index=True)
    descripcion = models.TextField()
    marca = models.CharField(max_length=100, db_index=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='productos',
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='productos_vendidos',
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('90.00'))],
    )
    stock = models.PositiveIntegerField(default=0)
    imagenes = models.JSONField(default=list, blank=True)
    especificaciones_tecnicas = models.JSONField(default=dict, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self) -> str:
        return f'{self.nombre} [{self.sku}]'

    @property
    def disponible(self) -> bool:
        return self.stock > 0

    @property
    def precio_con_descuento(self) -> Decimal:
        factor = (Decimal('100.00') - self.descuento_porcentaje) / Decimal('100.00')
        return (self.precio * factor).quantize(Decimal('0.01'))

    @property
    def rating_promedio(self) -> float:
        promedio = self.resenas.aggregate(avg=Avg('calificacion'))['avg']
        return round(float(promedio), 2) if promedio is not None else 0.0


class Resena(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resenas',
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='resenas',
    )
    calificacion = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    titulo = models.CharField(max_length=150)
    comentario = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        unique_together = ('usuario', 'producto')
        verbose_name = 'Reseña'
        verbose_name_plural = 'Reseñas'

    def __str__(self) -> str:
        return f'{self.producto.sku} - {self.calificacion}/5 por {self.usuario.username}'

    @property
    def es_compra_verificada(self) -> bool:
        return OrdenItem.objects.filter(
            orden__usuario=self.usuario,
            producto=self.producto,
            orden__estado__in=['pagada', 'enviada', 'entregada'],
        ).exists()


class Carrito(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carritos',
    )
    cupon = models.ForeignKey(
        Cupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carritos',
    )
    activo = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-actualizado_en']

    def __str__(self) -> str:
        estado = 'Activo' if self.activo else 'Cerrado'
        return f'Carrito #{self.pk} - {self.usuario.username} ({estado})'

    @property
    def cantidad_items(self) -> int:
        return sum(item.cantidad for item in self.items.all())

    @property
    def subtotal(self) -> Decimal:
        total = sum(
            (item.producto.precio_con_descuento * Decimal(item.cantidad) for item in self.items.all()),
            Decimal('0.00'),
        )
        return total.quantize(Decimal('0.01'))

    @property
    def impuestos(self) -> Decimal:
        return (self.subtotal * Decimal('0.18')).quantize(Decimal('0.01'))

    @property
    def total(self) -> Decimal:
        return (self.subtotal + self.impuestos).quantize(Decimal('0.01'))

    @property
    def total_con_descuento(self) -> Decimal:
        if self.cupon and self.cupon.activo:
            factor = (Decimal('100.00') - self.cupon.descuento_porcentaje) / Decimal('100.00')
            return (self.total * factor).quantize(Decimal('0.01'))
        return self.total


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE,
        related_name='items',
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='items_carrito',
    )
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ('carrito', 'producto')

    def __str__(self) -> str:
        return f'{self.cantidad} x {self.producto.nombre}'


class Orden(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('enviada', 'Enviada'),
        ('entregada', 'Entregada'),
        ('cancelada', 'Cancelada'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ordenes',
    )
    direccion_envio = models.TextField()
    metodo_pago = models.CharField(max_length=60)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    numero_seguimiento = models.CharField(max_length=60, blank=True, null=True, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'

    def __str__(self) -> str:
        return f'Orden #{self.pk} - {self.usuario.username} ({self.estado})'

    def save(self, *args, **kwargs):
        if self.estado == 'enviada' and not self.numero_seguimiento:
            self.numero_seguimiento = f'TKM-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)

    @property
    def tiempo_estimado_entrega(self) -> dict:
        base_date = (self.fecha_creacion or timezone.now()).date()
        return {
            'min_dias': 3,
            'max_dias': 5,
            'fecha_minima': (base_date + timedelta(days=3)).isoformat(),
            'fecha_maxima': (base_date + timedelta(days=5)).isoformat(),
        }


class OrdenItem(models.Model):
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name='items',
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='items_orden',
    )
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f'{self.cantidad} x {self.producto.nombre} @ {self.precio_unitario}'