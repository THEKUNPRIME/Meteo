import logging

import flet as ft

from weather_api import WeatherAPIError, fetch_weather


LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("app").setLevel(LOG_LEVEL)

BG = ft.Colors.BLUE_GREY_900
PANEL = ft.Colors.BLUE_GREY_800
PANEL_LIGHT = ft.Colors.BLUE_GREY_700
TEXT = ft.Colors.BLUE_GREY_50
MUTED = ft.Colors.BLUE_GREY_200
ACCENT = ft.Colors.AMBER_300
BLUE = ft.Colors.LIGHT_BLUE_300


def shown(value, suffix=""):
    return "-" if value is None else f"{value}{suffix}"


async def main(page: ft.Page):
    page.title = "Météo Claire"
    page.bgcolor = BG
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK

    city_input = ft.TextField(
        value="Paris", hint_text="Rechercher une ville", prefix_icon=ft.Icons.SEARCH,
        bgcolor=PANEL, color=TEXT, width=310,
        border=ft.OutlineInputBorder(border_radius=14, side=ft.BorderSide(color=PANEL_LIGHT)),
        content_padding=ft.Padding.symmetric(horizontal=16, vertical=12),
    )
    city_name = ft.Text("-", size=20, weight=ft.FontWeight.W_600, color=TEXT)
    temperature = ft.Text("-", size=92, weight=ft.FontWeight.W_500, color=TEXT)
    condition = ft.Text("-", size=21, color=TEXT)
    feels = ft.Text("Ressenti -  ·  Max - / Min -", size=14, color=MUTED)
    humidity_value = ft.Text("-", size=24, weight=ft.FontWeight.W_600, color=TEXT)
    wind_value = ft.Text("-", size=24, weight=ft.FontWeight.W_600, color=TEXT)
    uv_value = ft.Text("-", size=24, weight=ft.FontWeight.W_600, color=TEXT)
    sunrise_value = ft.Text("-", size=17, weight=ft.FontWeight.W_600, color=TEXT)
    sunset_value = ft.Text("-", size=17, weight=ft.FontWeight.W_600, color=TEXT)
    status = ft.Text("Connexion à Open-Meteo…", size=12, color=MUTED, max_lines=1,
                     overflow=ft.TextOverflow.ELLIPSIS)
    main_weather_icon = ft.Icon(ft.Icons.CLOUD, size=116, color=ACCENT)
    hourly_refs = []
    daily_refs = []

    def panel(content, *, padding=22, expand=False, width=None):
        return ft.Container(
            content=content, padding=padding, bgcolor=PANEL,
            border_radius=22, expand=expand, width=width,
        )

    def metric(icon, label, value_control, color):
        return panel(ft.Column(spacing=14, controls=[
            ft.Row(spacing=9, controls=[ft.Icon(icon, color=color, size=20), ft.Text(label, size=14, color=MUTED)]),
            value_control,
        ]), expand=True)

    async def load_city():
        city = (city_input.value or "").strip()
        if not city:
            status.value = "Saisissez le nom d’une ville."
            page.update()
            return

        status.value = "Recherche météo…"
        page.update()
        try:
            data = await fetch_weather(city)
        except WeatherAPIError as exc:
            status.value = str(exc)
            page.update()
            return

        city_name.value = data["location"] or "-"
        temperature.value = shown(data["temperature"], "°")
        condition.value = data["condition"] or "-"
        feels.value = (
            f"Ressenti {shown(data['feels_like'], '°')}  ·  "
            f"Max {shown(data['high'], '°')} / Min {shown(data['low'], '°')}"
        )
        humidity_value.value = shown(data["humidity"], " %")
        wind_value.value = shown(data["wind"], " km/h")
        uv = data["uv"]
        uv_level = "Faible" if uv is not None and uv < 3 else "Modéré" if uv is not None and uv < 6 else "Élevé" if uv is not None else None
        uv_value.value = "-" if uv is None else f"{uv} · {uv_level}"
        sunrise_value.value = data["sunrise"] or "-"
        sunset_value.value = data["sunset"] or "-"
        main_weather_icon.icon = getattr(ft.Icons, data["icon"])
        main_weather_icon.color = ACCENT if data["icon"] == "WB_SUNNY" else BLUE

        for index, (label_control, icon_control, temp_control) in enumerate(hourly_refs):
            item = data["hourly"][index] if index < len(data["hourly"]) else {}
            label_control.value = item.get("label") or "-"
            icon_control.icon = getattr(ft.Icons, item.get("icon", "CLOUD"))
            temp_control.value = shown(item.get("temperature"), "°")

        for index, (label_control, icon_control, high_control, low_control) in enumerate(daily_refs):
            item = data["daily"][index] if index < len(data["daily"]) else {}
            label_control.value = item.get("label") or "-"
            icon_control.icon = getattr(ft.Icons, item.get("icon", "CLOUD"))
            high_control.value = shown(item.get("high"), "°")
            low_control.value = shown(item.get("low"), "°")

        status.value = "Données en direct · Open-Meteo"
        page.update()

    city_input.on_submit = load_city

    hourly_controls = []
    for _ in range(6):
        label = ft.Text("-", size=12, color=MUTED)
        icon = ft.Icon(ft.Icons.CLOUD, size=23, color=ACCENT)
        temp = ft.Text("-", size=17, weight=ft.FontWeight.W_600, color=TEXT)
        hourly_refs.append((label, icon, temp))
        hourly_controls.append(ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=11,
                                         controls=[label, icon, temp]))

    day_controls = []
    for _ in range(5):
        label = ft.Text("-", size=13, color=MUTED)
        icon = ft.Icon(ft.Icons.CLOUD, size=25, color=ACCENT)
        high = ft.Text("-", color=TEXT, weight=ft.FontWeight.W_600)
        low = ft.Text("-", color=MUTED)
        daily_refs.append((label, icon, high, low))
        day_controls.append(ft.Column(expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                      spacing=12, controls=[label, icon,
                                      ft.Row(tight=True, spacing=10, controls=[high, low])]))

    content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=24, controls=[
        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Row(spacing=13, controls=[
                ft.Container(width=44, height=44, alignment=ft.Alignment.CENTER, bgcolor=ft.Colors.AMBER_400,
                             border_radius=14, content=ft.Icon(ft.Icons.WB_SUNNY, color=BG, size=25)),
                ft.Column(tight=True, spacing=1, controls=[ft.Text("météo", size=22, weight=ft.FontWeight.BOLD, color=TEXT),
                                                          ft.Text("LE TEMPS, EN CLAIR", size=10, color=MUTED)]),
            ]),
            ft.Row(spacing=14, controls=[city_input, ft.IconButton(ft.Icons.SEARCH, icon_color=TEXT,
                bgcolor=PANEL_LIGHT, tooltip="Rechercher", on_click=load_city)]),
        ]),
        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.END, controls=[
            ft.Column(tight=True, spacing=7, controls=[ft.Text("VOTRE MÉTÉO", size=11, color=BLUE,
                weight=ft.FontWeight.BOLD), city_name]),
            ft.Container(padding=ft.Padding.symmetric(horizontal=13, vertical=8), bgcolor=PANEL,
                         border_radius=20, content=ft.Row(tight=True, spacing=7, controls=[
                             ft.Container(width=7, height=7, bgcolor=ft.Colors.GREEN_300, border_radius=8), status])),
        ]),
        ft.Row(intrinsic_height=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH, spacing=20, controls=[
            panel(ft.Row(expand=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                         vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Column(expand=True, spacing=2, controls=[temperature, condition, feels,
                    ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.LOCATION_ON, size=17, color=BLUE),
                                               ft.Text("Conditions actuelles", size=13, color=MUTED)])]),
                ft.Container(width=205, height=205, alignment=ft.Alignment.CENTER, bgcolor=ft.Colors.BLUE_GREY_700,
                             border_radius=110, content=main_weather_icon),
            ]), padding=30, expand=True),
            panel(ft.Column(spacing=22, controls=[
                ft.Text("Soleil & lumière", size=17, weight=ft.FontWeight.W_600, color=TEXT),
                ft.Row(spacing=13, controls=[ft.Icon(ft.Icons.WB_TWILIGHT, color=ACCENT, size=22),
                    ft.Column(tight=True, spacing=3, controls=[ft.Text("Lever du soleil", size=12, color=MUTED), sunrise_value])]),
                ft.Divider(color=PANEL_LIGHT, thickness=1),
                ft.Row(spacing=13, controls=[ft.Icon(ft.Icons.WB_TWILIGHT, color=BLUE, size=22),
                    ft.Column(tight=True, spacing=3, controls=[ft.Text("Coucher du soleil", size=12, color=MUTED), sunset_value])]),
                ft.Container(expand=True), ft.Text("Prévisions locales", size=12, color=MUTED),
            ]), padding=24, width=260),
        ]),
        ft.Row(spacing=16, controls=[
            metric(ft.Icons.WATER_DROP, "Humidité", humidity_value, BLUE),
            metric(ft.Icons.AIR, "Vent", wind_value, ft.Colors.CYAN_200),
            metric(ft.Icons.WB_SUNNY, "Indice UV", uv_value, ACCENT),
        ]),
        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
            ft.Text("Aujourd’hui, heure par heure", size=18, weight=ft.FontWeight.W_600, color=TEXT),
            ft.Text("Prévisions horaires", size=12, color=BLUE),
        ]),
        panel(ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=hourly_controls), padding=24),
        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
            ft.Text("Les prochains jours", size=18, weight=ft.FontWeight.W_600, color=TEXT),
            ft.Text("5 jours", size=12, color=BLUE),
        ]),
        panel(ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=day_controls), padding=24),
        ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[ft.Text(
            "MÉTÉO CLAIRE  ·  DONNÉES FOURNIES PAR OPEN-METEO", size=10, color=MUTED)]),
    ])

    page.add(ft.Container(expand=True, alignment=ft.Alignment.TOP_CENTER,
        padding=ft.Padding.symmetric(horizontal=48, vertical=32),
        content=ft.Container(width=1320, content=content)))
    await load_city()


ft.run(main)
