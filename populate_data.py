import os
from decimal import Decimal
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from tienda.models import (
    Categoria,
    Cupon,
    Orden,
    OrdenItem,
    PerfilEcommerce,
    Producto,
    Resena,
)

User = get_user_model()


def run():
    categorias_info = [
        ("Laptops", "Laptops para oficina, gaming y desarrollo", "https://example.com/cat-laptops.jpg"),
        ("Smartphones", "Teléfonos inteligentes y equipos móviles", "https://example.com/cat-phones.jpg"),
        ("Componentes", "Procesadores, placas, memorias y almacenamiento", "https://example.com/cat-comp.jpg"),
        ("Accesorios", "Teclados, mouse, headsets y hubs", "https://example.com/cat-acc.jpg"),
    ]
    categorias = []
    for nombre, desc, img in categorias_info:
        cat, _ = Categoria.objects.get_or_create(
            nombre=nombre,
            defaults={"descripcion": desc, "imagen": img},
        )
        categorias.append(cat)

    Cupon.objects.get_or_create(
        codigo="TECH10",
        defaults={"descuento_porcentaje": Decimal("10.00"), "activo": True},
    )

    usuarios = []
    for i in range(1, 23):
        username = f"user_ecom_{i:02d}"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": f"Cliente{i}",
                "last_name": f"Lima{i}",
                "email": f"{username}@tecnomarket.pe",
                "is_staff": i == 1,
            },
        )
        if created:
            user.set_password("Clave1234!")
            user.save()
        Token.objects.get_or_create(user=user)
        rol = "administrador" if i == 1 else ("vendedor" if i in (2, 3) else "cliente")
        PerfilEcommerce.objects.get_or_create(
            usuario=user,
            defaults={
                "rol": rol,
                "telefono": f"999100{i:03d}",
                "direccion_predeterminada": f"Av. Javier Prado {1000 + i}, Lima",
                "puntos_fidelidad": i * 25,
            },
        )
        usuarios.append(user)

    vendedores = [usuarios[1], usuarios[2]]
    marcas = ["Dell", "Lenovo", "Asus", "Apple", "Samsung", "Kingston"]

    productos = []
    for idx in range(1, 106):
        sku = f"TKM-{idx:04d}"
        cat = categorias[idx % len(categorias)]
        marca = marcas[idx % len(marcas)]
        prod, _ = Producto.objects.get_or_create(
            sku=sku,
            defaults={
                "nombre": f"{marca} {cat.nombre[:-1]} Pro {idx:03d}",
                "descripcion": f"Equipo tecnológico {marca} modelo {idx:03d} para uso intensivo.",
                "marca": marca,
                "categoria": cat,
                "vendedor": vendedores[idx % len(vendedores)],
                "precio": Decimal("150.00") + Decimal(idx * 25),
                "descuento_porcentaje": Decimal("15.00") if idx % 5 == 0 else Decimal("0.00"),
                "stock": 20 + (idx % 15),
                "imagenes": [f"https://example.com/img/{sku.lower()}-1.jpg"],
                "especificaciones_tecnicas": {"garantia": "12 meses", "modelo": f"M-{idx:03d}"},
            },
        )
        productos.append(prod)

    clientes = usuarios[3:]
    estados_orden = ["pendiente", "pagada", "enviada", "entregada", "cancelada"]
    while Orden.objects.count() < 55:
        n = Orden.objects.count() + 1
        cli = clientes[n % len(clientes)]
        prod = productos[n % len(productos)]
        estado = estados_orden[n % len(estados_orden)]
        orden = Orden.objects.create(
            usuario=cli,
            direccion_envio=f"Calle Las Begonias {200 + n}, San Isidro, Lima",
            metodo_pago="tarjeta" if n % 2 == 0 else "yape",
            estado=estado,
            total=prod.precio_con_descuento,
        )
        OrdenItem.objects.create(
            orden=orden,
            producto=prod,
            cantidad=1,
            precio_unitario=prod.precio_con_descuento,
        )

    idx_r = 0
    while Resena.objects.count() < 110 and idx_r < 300:
        cli = clientes[idx_r % len(clientes)]
        prod = productos[idx_r % len(productos)]
        Resena.objects.get_or_create(
            usuario=cli,
            producto=prod,
            defaults={
                "calificacion": 1 + (idx_r % 5),
                "titulo": f"Reseña #{idx_r + 1}",
                "comentario": "Buen rendimiento y entrega conforme en TecnoMarket.",
            },
        )
        idx_r += 1

    print(
        f"OK -> Productos: {Producto.objects.count()} | "
        f"Usuarios: {User.objects.count()} | "
        f"Órdenes: {Orden.objects.count()} | "
        f"Reseñas: {Resena.objects.count()}"
    )


if __name__ == "__main__":
    run()