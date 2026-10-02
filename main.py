import importlib.util
import os
from datetime import date

from nicegui import app, ui

import db
import exportar

EXPORT_DIR = db.APP_DIR / "exportaciones"


def tiene_webview():
    return importlib.util.find_spec("webview") is not None


def fmt_dinero(valor):
    moneda = db.get_config("moneda", "MXN")
    return f"${valor:,.2f} {moneda}"


class Estado:
    def __init__(self):
        self.editando = None


estado = Estado()


@ui.page("/")
def pagina_principal():
    db.init_db()

    ui.colors(primary="#1F4E78")

    with ui.header().classes("items-center justify-between"):
        ui.label("Me-Paga").classes("text-2xl font-bold")
        etiqueta_titular = ui.label().classes("text-sm opacity-80")

    tarjetas = {}
    with ui.row().classes("w-full gap-4 q-pa-md"):
        for clave, titulo, color in [
            ("total", "Total abonado", "text-green-700"),
            ("saldo", "Saldo pendiente", "text-red-700"),
            ("deuda", "Deuda inicial", "text-blue-700"),
            ("cuenta", "Numero de abonos", "text-gray-700"),
        ]:
            with ui.card().classes("flex-1 items-center"):
                ui.label(titulo).classes("text-sm text-gray-500")
                tarjetas[clave] = ui.label("-").classes(f"text-2xl font-bold {color}")

    tabla = ui.table(
        columns=[
            {"name": "fecha", "label": "Fecha", "field": "fecha", "align": "center", "sortable": True},
            {"name": "monto", "label": "Abono", "field": "monto_fmt", "align": "right", "sortable": True},
            {"name": "metodo", "label": "Metodo", "field": "metodo", "align": "left"},
            {"name": "nota", "label": "Nota", "field": "nota", "align": "left"},
            {"name": "acciones", "label": "", "field": "acciones"},
        ],
        rows=[],
        row_key="id",
    ).classes("w-full")

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

    def refrescar():
        abonos = db.list_abonos()
        filas = []
        for a in abonos:
            filas.append(
                {
                    "id": a["id"],
                    "fecha": a["fecha"],
                    "monto": a["monto"],
                    "monto_fmt": fmt_dinero(a["monto"]),
                    "metodo": a.get("metodo", ""),
                    "nota": a.get("nota", ""),
                }
            )
        tabla.rows = filas
        tabla.update()
        tarjetas["total"].set_text(fmt_dinero(db.total_abonado()))
        tarjetas["saldo"].set_text(fmt_dinero(db.saldo_pendiente()))
        tarjetas["deuda"].set_text(fmt_dinero(db.get_deuda_inicial()))
        tarjetas["cuenta"].set_text(str(db.contar_abonos()))
        etiqueta_titular.set_text(f"Titular: {db.get_config('titular', 'Tia')}")

    def abrir_dialogo(abono=None):
        estado.editando = abono["id"] if abono else None
        with ui.dialog() as dialogo, ui.card().classes("w-96"):
            ui.label("Editar abono" if abono else "Nuevo abono").classes("text-lg font-bold")
            f_fecha = ui.input(
                "Fecha (dd/mm/aaaa)",
                value=abono["fecha"] if abono else date.today().strftime("%d/%m/%Y"),
            ).classes("w-full")
            f_monto = ui.input(
                "Monto", value=str(abono["monto"]) if abono else ""
            ).classes("w-full")
            f_metodo = ui.select(
                db.METODOS,
                label="Metodo",
                value=abono.get("metodo") if abono and abono.get("metodo") in db.METODOS else db.METODOS[0],
            ).classes("w-full")
            f_nota = ui.input(
                "Nota", value=abono.get("nota", "") if abono else ""
            ).classes("w-full")

            def guardar():
                try:
                    if estado.editando:
                        db.update_abono(
                            estado.editando, f_fecha.value, f_monto.value, f_metodo.value, f_nota.value
                        )
                        ui.notify("Abono actualizado", color="positive")
                    else:
                        db.add_abono(f_fecha.value, f_monto.value, f_metodo.value, f_nota.value)
                        ui.notify("Abono registrado", color="positive")
                    dialogo.close()
                    refrescar()
                except ValueError as e:
                    ui.notify(str(e), color="negative")

            with ui.row().classes("w-full justify-end"):
                ui.button("Cancelar", on_click=dialogo.close).props("flat")
                ui.button("Guardar", on_click=guardar).props("color=primary")
        dialogo.open()

    def confirmar_borrado(abono):
        with ui.dialog() as dialogo, ui.card():
            ui.label(f"Eliminar el abono de {fmt_dinero(abono['monto'])} del {abono['fecha']}?")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancelar", on_click=dialogo.close).props("flat")

                def borrar():
                    db.delete_abono(abono["id"])
                    dialogo.close()
                    refrescar()
                    ui.notify("Abono eliminado", color="warning")

                ui.button("Eliminar", on_click=borrar).props("color=negative")
        dialogo.open()

    tabla.on("editar", lambda e: abrir_dialogo(e.args))
    tabla.on("borrar", lambda e: confirmar_borrado(e.args))

    def abrir_configuracion():
        with ui.dialog() as dialogo, ui.card().classes("w-96"):
            ui.label("Configuracion").classes("text-lg font-bold")
            c_titular = ui.input("Titular", value=db.get_config("titular", "Tia")).classes("w-full")
            c_deuda = ui.input("Deuda inicial", value=str(db.get_deuda_inicial())).classes("w-full")
            c_moneda = ui.input("Moneda", value=db.get_config("moneda", "MXN")).classes("w-full")

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

            with ui.row().classes("w-full justify-end"):
                ui.button("Cancelar", on_click=dialogo.close).props("flat")
                ui.button("Guardar", on_click=guardar_config).props("color=primary")
        dialogo.open()

    def exportar_archivo():
        if db.contar_abonos() == 0:
            ui.notify("No hay abonos que exportar", color="warning")
            return
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        nombre = f"me-paga_{date.today().isoformat()}.xlsx"
        ruta = EXPORT_DIR / nombre
        exportar.exportar_excel(str(ruta))
        ui.download(str(ruta))
        ui.notify(f"Excel generado: {ruta}", color="positive")

    with ui.footer().classes("justify-between items-center"):
        ui.button("Nuevo abono", icon="add", on_click=lambda: abrir_dialogo()).props("color=primary")
        with ui.row():
            ui.button("Exportar a Excel", icon="download", on_click=exportar_archivo).props("color=green")
            ui.button("Configuracion", icon="settings", on_click=abrir_configuracion).props("flat")

    refrescar()


def iniciar():
    db.init_db()
    nativo = tiene_webview() and os.environ.get("ME_PAGA_BROWSER") != "1"
    ui.run(
        native=nativo,
        title="Me-Paga",
        reload=False,
        port=int(os.environ.get("ME_PAGA_PORT", "8777")),
        window_size=(1000, 720) if nativo else None,
        storage_secret="me-paga-local",
    )


if __name__ in {"__main__", "__mp_main__"}:
    iniciar()
