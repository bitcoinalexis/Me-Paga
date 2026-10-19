from datetime import date, datetime

import flet as ft

import almacen
import exportacion

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

BLANCO = "#FFFFFF"
FONDO = "#F2F2F7"
TEXTO = "#1D1D1F"
MUTED = "#6E6E73"
VERDE = "#18794E"
ROJO = "#C01230"
AZUL = "#0062CC"
GRIS = "#55555C"


def fmt_monto(valor):
    return f"${abs(valor):,.2f}"


def fmt_fecha_larga(iso):
    try:
        d = date.fromisoformat(iso)
        return f"{d.day} de {MESES[d.month - 1]} de {d.year}"
    except (ValueError, TypeError):
        return iso


def main(page: ft.Page):
    almacen.init_db()

    page.title = "Me-Paga"
    page.bgcolor = FONDO
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    titulo = ft.Text("Me-Paga", size=28, weight=ft.FontWeight.BOLD, color=TEXTO)
    subtitulo = ft.Text("", size=13, color=MUTED)

    def tarjeta(titulo_texto):
        etiqueta = ft.Text(titulo_texto, size=12, color=MUTED, weight=ft.FontWeight.W_600)
        valor = ft.Text("-", size=20, weight=ft.FontWeight.BOLD, color=TEXTO)
        contenedor = ft.Container(
            content=ft.Column([etiqueta, valor], spacing=2, tight=True),
            bgcolor=BLANCO,
            border_radius=16,
            padding=ft.Padding(14, 12, 14, 12),
            expand=True,
        )
        return contenedor, etiqueta, valor

    t_total, l_total, v_total = tarjeta("Total abonado")
    t_saldo, l_saldo, v_saldo = tarjeta("Saldo pendiente")
    t_deuda, l_deuda, v_deuda = tarjeta("Deuda inicial")
    t_cuenta, l_cuenta, v_cuenta = tarjeta("Abonos")

    lista = ft.ListView(expand=True, spacing=8, padding=ft.Padding(0, 4, 0, 90))

    def avisar(mensaje, color=VERDE):
        page.show_dialog(ft.SnackBar(ft.Text(mensaje), bgcolor=color))

    def refrescar():
        abonos = almacen.list_abonos()
        moneda = almacen.get_config("moneda", "MXN")
        total = almacen.total_abonado()
        deuda = almacen.get_deuda_inicial()
        saldo = almacen.saldo_pendiente()

        v_total.value = f"{fmt_monto(total)} {moneda}"
        v_total.color = VERDE
        v_deuda.value = f"{fmt_monto(deuda)} {moneda}"
        v_deuda.color = AZUL
        v_cuenta.value = str(almacen.contar_abonos())
        v_cuenta.color = GRIS

        if deuda <= 0:
            l_saldo.value = "Sin deuda registrada"
            v_saldo.value = f"{fmt_monto(0)} {moneda}"
            v_saldo.color = GRIS
        elif saldo > 0:
            l_saldo.value = "Saldo pendiente"
            v_saldo.value = f"{fmt_monto(saldo)} {moneda}"
            v_saldo.color = ROJO
        elif saldo == 0:
            l_saldo.value = "Deuda liquidada"
            v_saldo.value = f"{fmt_monto(0)} {moneda}"
            v_saldo.color = VERDE
        else:
            l_saldo.value = "Pago de mas"
            v_saldo.value = f"{fmt_monto(saldo)} {moneda}"
            v_saldo.color = VERDE

        subtitulo.value = f"Pagos de {almacen.get_config('titular', 'Tia')}"

        lista.controls.clear()
        if not abonos:
            lista.controls.append(
                ft.Container(
                    content=ft.Text("Aun no hay abonos registrados", color=MUTED, size=14),
                    alignment=ft.Alignment.CENTER,
                    padding=30,
                )
            )
        for a in abonos:
            lista.controls.append(fila_abono(a, moneda))
        page.update()

    def fila_abono(abono, moneda):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                f"{fmt_monto(abono['monto'])} {moneda}",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=TEXTO,
                            ),
                            ft.Text(fmt_fecha_larga(abono["fecha"]), size=12, color=MUTED),
                            ft.Text(
                                abono.get("metodo", "") + (
                                    f" - {abono['nota']}" if abono.get("nota") else ""
                                ),
                                size=12,
                                color=MUTED,
                            ),
                        ],
                        spacing=2,
                        tight=True,
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_color=AZUL,
                        on_click=lambda e, a=abono: abrir_editor(a),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ROJO,
                        on_click=lambda e, a=abono: confirmar_borrado(a),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=BLANCO,
            border_radius=14,
            padding=ft.Padding(14, 10, 6, 10),
        )

    def abrir_editor(abono=None):
        base = date.fromisoformat(abono["fecha"]) if abono else date.today()
        seleccion = {"fecha": base}

        def cambio_fecha(e):
            valor = e.control.value
            seleccion["fecha"] = valor.date() if isinstance(valor, datetime) else valor

        rueda = ft.CupertinoDatePicker(
            value=datetime(base.year, base.month, base.day),
            date_picker_mode=ft.CupertinoDatePickerMode.DATE,
            on_change=cambio_fecha,
        )

        campo_monto = ft.TextField(
            label="Monto",
            value=str(abono["monto"]) if abono else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=12,
        )
        campo_metodo = ft.Dropdown(
            label="Metodo",
            value=abono.get("metodo") if abono and abono.get("metodo") in almacen.METODOS else almacen.METODOS[0],
            options=[ft.DropdownOption(key=m, text=m) for m in almacen.METODOS],
            border_radius=12,
        )
        campo_nota = ft.TextField(
            label="Nota", value=abono.get("nota", "") if abono else "", border_radius=12
        )

        def guardar(e):
            try:
                if abono:
                    almacen.update_abono(
                        abono["id"], seleccion["fecha"], campo_monto.value,
                        campo_metodo.value, campo_nota.value,
                    )
                else:
                    almacen.add_abono(
                        seleccion["fecha"], campo_monto.value,
                        campo_metodo.value, campo_nota.value,
                    )
                page.pop_dialog()
                refrescar()
                avisar("Abono guardado")
            except ValueError as err:
                avisar(str(err), ROJO)

        dialogo = ft.AlertDialog(
            title=ft.Text("Editar abono" if abono else "Nuevo abono"),
            content=ft.Column(
                [
                    ft.Text("Fecha", size=12, color=MUTED),
                    ft.Container(content=rueda, height=180),
                    campo_monto,
                    campo_metodo,
                    campo_nota,
                ],
                tight=True,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                width=340,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton("Guardar", on_click=guardar),
            ],
        )
        page.show_dialog(dialogo)

    def confirmar_borrado(abono):
        def borrar(e):
            almacen.delete_abono(abono["id"])
            page.pop_dialog()
            refrescar()
            avisar("Abono eliminado", GRIS)

        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Eliminar abono"),
                content=ft.Text(
                    f"{fmt_monto(abono['monto'])} del {fmt_fecha_larga(abono['fecha'])}"
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.FilledButton("Eliminar", on_click=borrar),
                ],
            )
        )

    def abrir_configuracion(e=None):
        c_titular = ft.TextField(
            label="Titular", value=almacen.get_config("titular", "Tia"), border_radius=12
        )
        c_deuda = ft.TextField(
            label="Deuda inicial",
            value=str(almacen.get_deuda_inicial()),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=12,
        )
        c_moneda = ft.TextField(
            label="Moneda", value=almacen.get_config("moneda", "MXN"), border_radius=12
        )

        def guardar_config(ev):
            try:
                almacen.set_config("titular", (c_titular.value or "").strip() or "Tia")
                almacen.set_deuda_inicial(c_deuda.value)
                almacen.set_config("moneda", (c_moneda.value or "").strip() or "MXN")
                page.pop_dialog()
                refrescar()
                avisar("Configuracion guardada")
            except ValueError as err:
                avisar(str(err), ROJO)

        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Configuracion"),
                content=ft.Column([c_titular, c_deuda, c_moneda], tight=True, spacing=10, width=320),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda ev: page.pop_dialog()),
                    ft.FilledButton("Guardar", on_click=guardar_config),
                ],
            )
        )

    def exportar(formato):
        if almacen.contar_abonos() == 0:
            avisar("No hay abonos que exportar", GRIS)
            return
        nombre = f"me-paga_{date.today().isoformat()}.{formato}"
        ruta = almacen.directorio_exportaciones() / nombre
        if formato == "csv":
            exportacion.exportar_csv(str(ruta))
        else:
            exportacion.exportar_excel(str(ruta))
        avisar(f"Guardado en {ruta}")

    def menu_exportar(e=None):
        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Exportar"),
                content=ft.Text("Elige el formato del archivo"),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda ev: page.pop_dialog()),
                    ft.TextButton(
                        "CSV", on_click=lambda ev: (page.pop_dialog(), exportar("csv"))
                    ),
                    ft.FilledButton(
                        "Excel", on_click=lambda ev: (page.pop_dialog(), exportar("xlsx"))
                    ),
                ],
            )
        )

    page.appbar = ft.AppBar(
        title=ft.Column([titulo, subtitulo], spacing=0, tight=True),
        bgcolor=BLANCO,
        color=TEXTO,
        toolbar_height=72,
        actions=[
            ft.IconButton(ft.Icons.IOS_SHARE, icon_color=AZUL, on_click=menu_exportar),
            ft.IconButton(ft.Icons.SETTINGS, icon_color=AZUL, on_click=abrir_configuracion),
        ],
    )

    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        bgcolor=AZUL,
        foreground_color=BLANCO,
        on_click=lambda e: abrir_editor(),
    )

    page.add(
        ft.SafeArea(
            content=ft.Column(
                [
                    ft.Row([t_total, t_saldo], spacing=10),
                    ft.Row([t_deuda, t_cuenta], spacing=10),
                    lista,
                ],
                spacing=10,
                expand=True,
            ),
            expand=True,
        )
    )

    refrescar()


if __name__ == "__main__":
    ft.run(main)
