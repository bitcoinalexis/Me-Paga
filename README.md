# Me-Paga

App de escritorio para registrar los abonos de una deuda y exportarlos a Excel con formulas vivas.

## Instalar

```
pip install -r requirements.txt
```

## Ejecutar

```
python main.py
```

Se abre una ventana nativa de escritorio. Si `pywebview` no esta instalado, la app se abre en el navegador. Para forzar el navegador: `ME_PAGA_BROWSER=1 python main.py`.

## Que hace

- Registrar, editar y eliminar abonos (fecha, monto, metodo, nota).
- Tarjetas con total abonado, saldo pendiente, deuda inicial y numero de abonos.
- Configuracion del titular, deuda inicial y moneda.
- Exportar a Excel con formulas reales: `SUM`, `COUNT`, `AVERAGE` y el saldo pendiente calculado en la hoja.

## Datos

La base de datos SQLite y los Excel exportados se guardan en `~/.me-paga/`.

## Formatos aceptados

- Fecha: `dd/mm/aaaa`, `aaaa-mm-dd`, `dd-mm-aaaa`.
- Monto: admite `$`, comas de miles y espacios (`$1,200.50`).
