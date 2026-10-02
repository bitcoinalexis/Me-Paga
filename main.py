import calendar
import importlib.util
import os
from datetime import date

from nicegui import app, ui

import db
import exportar

EXPORT_DIR = db.APP_DIR / "exportaciones"

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

ESTILO_IOS = """
<style>
:root {
  --bg: #FFFFFF;
  --tile: #FFFFFF;
  --tile-top: #FFFFFF;
  --tile-bottom: #F4F6F9;
  --text: #1D1D1F;
  --muted: #6E6E73;
  --sep: rgba(0,0,0,0.08);
  --hover: rgba(0,0,0,0.028);
  --verde: #18794E;
  --rojo: #C01230;
  --azul: #0062CC;
  --gris: #55555C;
}
html, body, .q-page, .nicegui-content, .q-layout, .q-page-container {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
               "Helvetica Neue", "Segoe UI", Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}
.tile {
  position: relative;
  background: linear-gradient(180deg, var(--tile-top) 0%, var(--tile-bottom) 100%);
  border: 1px solid var(--sep);
  border-radius: 18px;
  padding: 16px 18px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.05), 0 10px 24px rgba(16,24,40,0.06);
  overflow: hidden;
}
.tile::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 46%;
  background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 100%);
  pointer-events: none;
}
.mosaico {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 14px;
  width: 100%;
}
.stat-lbl {
  font-size: 0.8rem;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 0.01em;
}
.stat-num {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  white-space: nowrap;
  line-height: 1.25;
  color: var(--text);
}
.stat-cur { font-size: 0.75rem; font-weight: 600; color: var(--muted); margin-left: 5px; }
.titulo { font-size: 2rem; font-weight: 800; letter-spacing: -0.03em; color: var(--text); }
.subtitulo { font-size: 0.95rem; color: var(--muted); }
.c-verde { color: var(--verde) !important; }
.c-rojo  { color: var(--rojo) !important; }
.c-azul  { color: var(--azul) !important; }
.c-gris  { color: var(--gris) !important; }
.q-btn { border-radius: 980px !important; text-transform: none !important; font-weight: 600; letter-spacing: 0; }
.tabla-tile {
  border: 1px solid var(--sep);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(16,24,40,0.05), 0 10px 24px rgba(16,24,40,0.06);
}
.tabla-tile, .tabla-tile .q-table__container, .tabla-tile table,
.tabla-tile thead tr, .tabla-tile .q-table__middle {
  background: #FFFFFF !important;
}
.tabla-tile thead th {
  color: var(--muted) !important;
  font-weight: 600;
  font-size: 0.8rem;
  background: linear-gradient(180deg, #FFFFFF 0%, #F4F6F9 100%) !important;
}
.tabla-tile tbody td { color: var(--text) !important; font-size: 0.95rem; }
.tabla-tile tbody tr:hover { background: var(--hover) !important; }
.tabla-tile td, .tabla-tile th { border-color: var(--sep) !important; }
.dialogo { border-radius: 22px !important; background: #FFFFFF !important; color: var(--text) !important; }
.q-field--outlined .q-field__control { border-radius: 12px; }
.q-field__native, .q-field__label, .q-item__label { color: var(--text) !important; }
</style>
"""


def tiene_webview():
    return importlib.util.find_spec("webview") is not None


def dias_en_mes(mes, anio):
    return calendar.monthrange(anio, mes)[1]


def fmt_monto(valor):
    return f"${abs(valor):,.2f}"


def fmt_dinero(valor):
    moneda = db.get_config("moneda", "MXN")
    return f"${valor:,.2f} {moneda}"


def fmt_fecha_larga(iso):
    try:
        d = date.fromisoformat(iso)
        return f"{d.day} de {MESES[d.month - 1]} de {d.year}"
    except (ValueError, TypeError):
        return iso


class Estado:
    def __init__(self):
        self.editando = None


estado = Estado()


@ui.page("/")
def pagina_principal():
    db.init_db()
    ui.add_head_html(ESTILO_IOS)
    ui.dark_mode(False)
    ui.colors(primary="#0062CC", positive="#18794E", negative="#C01230", warning="#9A5B00")

    with ui.column().classes("w-full max-w-4xl mx-auto q-pa-md gap-4"):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-0"):
                ui.label("Me-Paga").classes("titulo")
                etiqueta_titular = ui.label().classes("subtitulo")
            ui.button(icon="settings", on_click=lambda: abrir_configuracion()).props(
                "flat round color=primary"
            )

        tarjetas = {}
        with ui.element("div").classes("mosaico"):
            for clave, titulo in [
                ("total", "Total abonado"),
                ("saldo", "Saldo pendiente"),
                ("deuda", "Deuda inicial"),
                ("cuenta", "Abonos"),
            ]:
                with ui.column().classes("tile gap-1 items-start"):
                    etiqueta = ui.label(titulo).classes("stat-lbl")
                    with ui.row().classes("items-baseline gap-0 no-wrap"):
                        valor = ui.label("-").classes("stat-num")
                        unidad = ui.label("").classes("stat-cur")
                    tarjetas[clave] = (etiqueta, valor, unidad)

        tabla = ui.table(
            columns=[
                {"name": "fecha_larga", "label": "Fecha", "field": "fecha_larga", "align": "left", "sortable": True},
                {"name": "monto", "label": "Abono", "field": "monto_fmt", "align": "right", "sortable": True},
                {"name": "metodo", "label": "Metodo", "field": "metodo", "align": "left"},
                {"name": "nota", "label": "Nota", "field": "nota", "align": "left"},
                {"name": "acciones", "label": "", "field": "acciones"},
            ],
            rows=[],
            row_key="id",
        ).props("flat").classes("tabla-tile w-full")

        tabla.add_slot(
            "body-cell-acciones",
            r"""
            <q-td :props="props" class="text-right">
                <q-btn flat dense round icon="edit" color="primary"
                       @click="() => $parent.$emit('editar', props.row)" />
                <q-btn flat dense round icon="delete" color="negative"
                       @click="() => $parent.$emit('borrar', props.row)" />
            </q-td>
            """,
        )

        tabla.add_slot(
            "no-data",
            r"""
            <div class="full-width row flex-center q-pa-lg" style="color:#6E6E73">
                Aun no hay abonos registrados
            </div>
            """,
        )

        with ui.row().classes("w-full gap-3 no-wrap"):
            ui.button("Nuevo abono", icon="add", on_click=lambda: abrir_dialogo()).props(
                "color=primary unelevated"
            ).classes("flex-1")
            ui.button("Excel", icon="download", on_click=lambda: exportar_archivo("xlsx")).props(
                "color=positive unelevated"
            ).classes("flex-1")
            ui.button("CSV", icon="description", on_click=lambda: exportar_archivo("csv")).props(
                "color=primary outline"
            ).classes("flex-1")

    def refrescar():
        abonos = db.list_abonos()
        filas = []
        for a in abonos:
            filas.append(
                {
                    "id": a["id"],
                    "fecha": a["fecha"],
                    "fecha_larga": fmt_fecha_larga(a["fecha"]),
                    "monto": a["monto"],
                    "monto_fmt": fmt_dinero(a["monto"]),
                    "metodo": a.get("metodo", ""),
                    "nota": a.get("nota", ""),
                }
            )
        tabla.rows = filas
        tabla.update()

        moneda = db.get_config("moneda", "MXN")
        total = db.total_abonado()
        deuda = db.get_deuda_inicial()
        saldo = db.saldo_pendiente()

        def pintar(clave, titulo, texto, unidad, clase):
            etiqueta, valor, sufijo = tarjetas[clave]
            etiqueta.set_text(titulo)
            valor.set_text(texto)
            valor.classes(replace=f"stat-num {clase}")
            sufijo.set_text(unidad)

        pintar("total", "Total abonado", fmt_monto(total), moneda, "c-verde")
        pintar("deuda", "Deuda inicial", fmt_monto(deuda), moneda, "c-azul")

        if deuda <= 0:
            pintar("saldo", "Sin deuda registrada", fmt_monto(0), moneda, "c-gris")
        elif saldo > 0:
            pintar("saldo", "Saldo pendiente", fmt_monto(saldo), moneda, "c-rojo")
        elif saldo == 0:
            pintar("saldo", "Deuda liquidada", fmt_monto(0), moneda, "c-verde")
        else:
            pintar("saldo", "Pago de mas", fmt_monto(saldo), moneda, "c-verde")

        pintar("cuenta", "Abonos", str(db.contar_abonos()), "", "c-gris")
        etiqueta_titular.set_text(f"Pagos de {db.get_config('titular', 'Tia')}")

    def abrir_dialogo(abono=None):
        estado.editando = abono["id"] if abono else None
        with ui.dialog() as dialogo, ui.card().classes("dialogo w-96 gap-2"):
            ui.label("Editar abono" if abono else "Nuevo abono").classes("text-lg font-bold")

            hoy = date.today()
            base = date.fromisoformat(abono["fecha"]) if abono else hoy
            anios = list(range(2015, hoy.year + 2))

            ui.label("Fecha").classes("stat-lbl")
            with ui.row().classes("w-full gap-2 no-wrap"):
                f_mes = ui.select(
                    {i + 1: m for i, m in enumerate(MESES)},
                    label="Mes",
                    value=base.month,
                ).props("outlined").classes("flex-1")
                f_dia = ui.select(
                    list(range(1, dias_en_mes(base.month, base.year) + 1)),
                    label="Dia",
                    value=base.day,
                ).props("outlined").classes("w-24")
                f_anio = ui.select(anios, label="Anio", value=base.year).props("outlined").classes("w-28")

            def ajustar_dias():
                maxd = dias_en_mes(f_mes.value, f_anio.value)
                f_dia.options = list(range(1, maxd + 1))
                if f_dia.value and f_dia.value > maxd:
                    f_dia.value = maxd
                f_dia.update()

            f_mes.on("update:model-value", lambda _: ajustar_dias())
            f_anio.on("update:model-value", lambda _: ajustar_dias())

            f_monto = ui.input("Monto", value=str(abono["monto"]) if abono else "").props(
                "outlined"
            ).classes("w-full")
            f_metodo = ui.select(
                db.METODOS,
                label="Metodo",
                value=abono.get("metodo") if abono and abono.get("metodo") in db.METODOS else db.METODOS[0],
            ).props("outlined").classes("w-full")
            f_nota = ui.input("Nota", value=abono.get("nota", "") if abono else "").props(
                "outlined"
            ).classes("w-full")

            def guardar():
                try:
                    fecha_sel = date(f_anio.value, f_mes.value, f_dia.value)
                    if estado.editando:
                        db.update_abono(
                            estado.editando, fecha_sel, f_monto.value, f_metodo.value, f_nota.value
                        )
                        ui.notify("Abono actualizado", color="positive")
                    else:
                        db.add_abono(fecha_sel, f_monto.value, f_metodo.value, f_nota.value)
                        ui.notify("Abono registrado", color="positive")
                    dialogo.close()
                    refrescar()
                except ValueError as e:
                    ui.notify(str(e), color="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialogo.close).props("flat color=primary")
                ui.button("Guardar", on_click=guardar).props("color=primary unelevated")
        dialogo.open()

    def confirmar_borrado(abono):
        with ui.dialog() as dialogo, ui.card().classes("dialogo gap-2"):
            ui.label("Eliminar abono").classes("text-lg font-bold")
            ui.label(f"{fmt_dinero(abono['monto'])} del {fmt_fecha_larga(abono['fecha'])}").classes(
                "subtitulo"
            )
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialogo.close).props("flat color=primary")

                def borrar():
                    db.delete_abono(abono["id"])
                    dialogo.close()
                    refrescar()
                    ui.notify("Abono eliminado", color="warning")

                ui.button("Eliminar", on_click=borrar).props("color=negative unelevated")
        dialogo.open()

    def abrir_configuracion():
        with ui.dialog() as dialogo, ui.card().classes("dialogo w-96 gap-2"):
            ui.label("Configuracion").classes("text-lg font-bold")
            c_titular = ui.input("Titular", value=db.get_config("titular", "Tia")).props(
                "outlined"
            ).classes("w-full")
            c_deuda = ui.input("Deuda inicial", value=str(db.get_deuda_inicial())).props(
                "outlined"
            ).classes("w-full")
            c_moneda = ui.input("Moneda", value=db.get_config("moneda", "MXN")).props(
                "outlined"
            ).classes("w-full")

            def guardar_config():
                try:
                    db.set_config("titular", c_titular.value.strip() or "Tia")
                    db.set_deuda_inicial(c_deuda.value)
                    db.set_config("moneda", c_moneda.value.strip() or "MXN")
                    dialogo.close()
                    refrescar()
                    ui.notify("Configuracion guardada", color="positive")
                except ValueError as e:
                    ui.notify(str(e), color="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialogo.close).props("flat color=primary")
                ui.button("Guardar", on_click=guardar_config).props("color=primary unelevated")
        dialogo.open()

    def exportar_archivo(formato="xlsx"):
        if db.contar_abonos() == 0:
            ui.notify("No hay abonos que exportar", color="warning")
            return
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        nombre = f"me-paga_{date.today().isoformat()}.{formato}"
        ruta = EXPORT_DIR / nombre
        if formato == "csv":
            exportar.exportar_csv(str(ruta))
        else:
            exportar.exportar_excel(str(ruta))
        ui.download(str(ruta))
        ui.notify(f"Archivo generado: {ruta}", color="positive")

    tabla.on("editar", lambda e: abrir_dialogo(e.args))
    tabla.on("borrar", lambda e: confirmar_borrado(e.args))

    refrescar()


def iniciar():
    db.init_db()
    nativo = tiene_webview() and os.environ.get("ME_PAGA_BROWSER") != "1"
    ui.run(
        native=nativo,
        title="Me-Paga",
        reload=False,
        port=int(os.environ.get("ME_PAGA_PORT", "8777")),
        window_size=(1040, 740) if nativo else None,
        storage_secret="me-paga-local",
    )


if __name__ in {"__main__", "__mp_main__"}:
    iniciar()
