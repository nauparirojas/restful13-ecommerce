# TecnoMarket Perú — RESTful API (Caso 2)

API REST desarrollada con **Django**, **Django REST Framework** y **drf-spectacular** sobre SQLite, incluyendo relaciones HATEOAS, snapshots de precios en órdenes, validación de compra en reseñas, paginación, filtros, throttling y documentación OpenAPI (`schema.yml`).

## Estructura principal
- `config/`: configuración del proyecto (`settings.py`, `urls.py`).
- `tienda/`: modelos, serializadores, vistas/ViewSets y rutas (`models.py`, `serializers.py`, `views.py`, `urls.py`).
- `populate_data.py`: script de población de datos iniciales (productos, usuarios, órdenes y reseñas).
- `schema.yml`: especificación OpenAPI generada con `drf-spectacular`.

## Ejecución local
```bash
python -m venv venv
# Windows (PowerShell): .\venv\Scripts\Activate.ps1
# Git Bash: source venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py populate_data
python manage.py spectacular --file schema.yml --validate
python manage.py runserver
