import os
import sys
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

if st.button("🔄 Actualizar Datos", use_container_width=True):
    st.rerun()

st.title("Banco del Austro")

EXCEL_URL = "https://docs.google.com/spreadsheets/d/19aw00haXlThBf0AlHwMsYNabeFGAbbjw/export?format=xlsx"


@st.cache_data(ttl=60)
def cargar_todas_las_hojas(url):
    return pd.read_excel(url, sheet_name=None)


def obtener_hoja(dict_hojas, nombre_buscado):
    for key in dict_hojas.keys():
        if key.strip().lower() == nombre_buscado.strip().lower():
            return dict_hojas[key]
    for key in dict_hojas.keys():
        if nombre_buscado.strip().lower() in key.strip().lower():
            return dict_hojas[key]
    return pd.DataFrame()


todas_las_hojas = cargar_todas_las_hojas(EXCEL_URL)

# 1. Retiros por Año, Total y Retiro / Día Global
df_raw_retiros = obtener_hoja(todas_las_hojas, "Retiros")
df_retiros = pd.DataFrame()
if (
    not df_raw_retiros.empty
    and "Fecha" in df_raw_retiros.columns
    and "Valor" in df_raw_retiros.columns
):
    df_retiros = df_raw_retiros[["Fecha", "Valor"]].dropna().copy()
    df_retiros["Fecha_dt"] = pd.to_datetime(
        df_retiros["Fecha"], format="%d/%m/%Y", dayfirst=True, errors="coerce"
    )
    df_retiros = df_retiros.dropna(subset=["Fecha_dt"]).sort_values("Fecha_dt")
    df_retiros["Año"] = df_retiros["Fecha_dt"].dt.year

if not df_retiros.empty:
    ultimo_retiro_row = df_retiros.iloc[-1]
    fecha_ultimo_retiro = ultimo_retiro_row["Fecha_dt"].strftime("%d/%m/%Y")
    valor_ultimo_retiro = ultimo_retiro_row["Valor"]
    txt_ultimo_retiro = f"{fecha_ultimo_retiro} — ${valor_ultimo_retiro:,.2f}"
else:
    txt_ultimo_retiro = "N/A"

tabla_anos = (
    df_retiros.groupby("Año")["Valor"]
    .agg(
        N_Retiros="count",
        Total_USD="sum",
    )
    .reset_index()
)
tabla_anos["Retiro_Dia"] = tabla_anos["Total_USD"] / 365
tabla_anos["Año"] = tabla_anos["Año"].astype(str)
tabla_anos.columns = ["Año", "Nº Retiros", "Total", "Retiro / Día"]

# 2. Transferencias Interbancarias
df_raw_trans = obtener_hoja(todas_las_hojas, "Transferencias Interbancarias")
df_trans_clean = pd.DataFrame()
if (
    not df_raw_trans.empty
    and "Institución" in df_raw_trans.columns
    and "Valor" in df_raw_trans.columns
):
    df_trans_clean = df_raw_trans[["Institución", "Valor"]].dropna().copy()
    df_trans_clean.loc[
        df_trans_clean["Institución"].str.contains(
            "JARDIN AZUAYO|Jardín Azuayo", case=False, na=False
        ),
        "Institución",
    ] = "Jardin Azuayo"

    tabla_trans = (
        df_trans_clean.groupby("Institución")["Valor"]
        .agg(
            N_Trans="count",
            Total_USD="sum",
        )
        .reset_index()
        .sort_values("Total_USD", ascending=False)
    )
    tabla_trans.columns = [
        "Entidad Financiera",
        "Nº Transferencias",
        "Total Transferido",
    ]
else:
    tabla_trans = pd.DataFrame(
        columns=["Entidad Financiera", "Nº Transferencias", "Total Transferido"]
    )


def dos_lineas_banco(nombre):
    nombre_str = str(nombre).strip()
    words = nombre_str.split()
    if len(words) == 2:
        return f"{words[0]}<br>{words[1]}"
    elif len(words) == 3 and words[1].lower() in ["de", "del", "la", "el"]:
        return f"{words[0]} {words[1]}<br>{words[2]}"
    elif len(words) > 1:
        mid = len(words) // 2
        return f"{' '.join(words[:mid])}<br>{' '.join(words[mid:])}"
    return nombre_str


if not tabla_trans.empty:
    tabla_trans["Entidad Financiera"] = tabla_trans["Entidad Financiera"].apply(
        dos_lineas_banco
    )

df_trans_fechas = pd.DataFrame()
if (
    not df_raw_trans.empty
    and "Fecha" in df_raw_trans.columns
    and "Valor" in df_raw_trans.columns
):
    df_trans_fechas = df_raw_trans[["Fecha", "Valor"]].dropna().copy()
    df_trans_fechas["Fecha_dt"] = pd.to_datetime(
        df_trans_fechas["Fecha"], format="%d/%m/%Y", dayfirst=True, errors="coerce"
    )
    df_trans_fechas = df_trans_fechas.dropna(subset=["Fecha_dt"]).sort_values(
        "Fecha_dt"
    )
    df_trans_fechas["Año"] = df_trans_fechas["Fecha_dt"].dt.year
    if not df_trans_fechas.empty:
        ultima_trans_row = df_trans_fechas.iloc[-1]
        fecha_ultima_trans = ultima_trans_row["Fecha_dt"].strftime("%d/%m/%Y")
        valor_ultima_trans = ultima_trans_row["Valor"]
        txt_ultima_trans = f"{fecha_ultima_trans} — ${valor_ultima_trans:,.2f}"
    else:
        txt_ultima_trans = "N/A"
else:
    txt_ultima_trans = "N/A"

# 3. Compras por Internet
df_raw_compras = obtener_hoja(todas_las_hojas, "Compras por internet")


def categorizar_descripcion(desc):
    desc_str = str(desc).upper()
    if "AMAZON" in desc_str or "AMZN" in desc_str:
        return "Amazon"
    elif "ALIEXPRESS" in desc_str or "ALIPAY" in desc_str:
        return "Aliexpress"
    elif "SHEIN" in desc_str:
        return "Shein"
    elif "EBAY" in desc_str:
        return "eBay"
    elif "TEMU" in desc_str:
        return "Temu"
    elif any(
        k in desc_str
        for k in [
            "TRANSEXPRES",
            "LAARBOX",
            "FLETE",
            "EXPRESSWEB",
            "TRANS EXPRESS",
        ]
    ):
        return "Flete Laarbox"
    elif "FARMASOL" in desc_str:
        return "Farmasol"
    else:
        return desc_str.strip()


df_compras = pd.DataFrame()
if (
    not df_raw_compras.empty
    and "Descripción" in df_raw_compras.columns
    and "Valor" in df_raw_compras.columns
):
    df_compras = df_raw_compras.copy()
    df_compras["Establecimiento"] = df_compras["Descripción"].apply(
        categorizar_descripcion
    )
    df_compras["Valor"] = pd.to_numeric(df_compras["Valor"], errors="coerce")
    df_compras = df_compras.dropna(subset=["Valor"])

    if "Fecha" in df_compras.columns:
        df_compras["Fecha_dt"] = pd.to_datetime(
            df_compras["Fecha"], format="%d/%m/%Y", dayfirst=True, errors="coerce"
        )
        df_compras = df_compras.dropna(subset=["Fecha_dt"])
        df_compras["Año"] = df_compras["Fecha_dt"].dt.year

    tabla_compras = (
        df_compras.groupby("Establecimiento", as_index=False)["Valor"]
        .agg(
            N_Compras="count",
            Total_USD="sum",
        )
        .sort_values("Total_USD", ascending=False)
        .reset_index(drop=True)
    )
    tabla_compras.columns = [
        "Establecimiento",
        "Nº Compras",
        "Total Comprado",
    ]
else:
    tabla_compras = pd.DataFrame(
        columns=["Establecimiento", "Nº Compras", "Total Comprado"]
    )

# 4. Swift
df_raw_swift = obtener_hoja(todas_las_hojas, "Swift")
df_swift = pd.DataFrame()
if not df_raw_swift.empty and "Valor" in df_raw_swift.columns:
    df_swift = df_raw_swift.copy()
    df_swift["Valor"] = pd.to_numeric(df_swift["Valor"], errors="coerce")
    df_swift = df_swift.dropna(subset=["Valor"])
    if "Fecha" in df_swift.columns:
        df_swift["Fecha_dt"] = pd.to_datetime(
            df_swift["Fecha"], format="%d/%m/%Y", dayfirst=True, errors="coerce"
        )
        df_swift = df_swift.dropna(subset=["Fecha_dt"])
        df_swift["Año"] = df_swift["Fecha_dt"].dt.year

# Obtener lista unificada de todos los años disponibles
anos_set = set()
for df_temp in [df_retiros, df_trans_fechas, df_compras, df_swift]:
    if "Año" in df_temp.columns:
        anos_set.update(df_temp["Año"].dropna().unique())

anos_disponibles = ["Todos"] + [str(int(y)) for y in sorted(anos_set)]


def render_custom_table(df):
    css = """
    <style>
    .table-container {
        max-height: 420px;
        width: fit-content;
        max-width: 100%;
        overflow-x: auto;
        overflow-y: auto;
        padding: 0px;
        border: 2px solid #000000;
        border-radius: 8px;
        margin-bottom: 20px;
        background-color: #FFFFFF;
    }
    .custom-table {
        width: max-content;
        border-collapse: separate;
        border-spacing: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 14px;
        color: #000000 !important;
    }
    .custom-table th {
        position: sticky !important;
        top: 0 !important;
        z-index: 20 !important;
        background-color: #FFEB3B !important;
        color: #000000 !important;
        text-align: center !important;
        padding: 10px 14px;
        font-weight: bold;
        white-space: nowrap;
        border-bottom: 1px solid #000000;
        border-right: 1px solid #000000;
        width: max-content !important;
    }
    .custom-table th.col-sticky {
        position: sticky !important;
        left: 0 !important;
        top: 0 !important;
        z-index: 50 !important;
        width: max-content !important;
        white-space: nowrap !important;
        background-color: #FFEB3B !important;
        color: #000000 !important;
        box-shadow: 2px 0 5px rgba(0,0,0,0.2);
    }
    .custom-table td {
        position: static !important;
        z-index: auto !important;
        text-align: center !important;
        padding: 10px 14px;
        white-space: nowrap;
        color: #000000 !important;
        font-weight: 600;
        border-bottom: 1px solid #000000;
        border-right: 1px solid #000000;
        width: max-content !important;
    }
    .custom-table td.col-sticky {
        position: sticky !important;
        left: 0 !important;
        z-index: 30 !important;
        width: max-content !important;
        white-space: nowrap !important;
        background-color: #FFEB3B !important;
        background-clip: padding-box !important;
        font-weight: bold;
        color: #000000 !important;
        box-shadow: 2px 0 5px rgba(0,0,0,0.2);
    }
    .row-even td:not(.col-sticky) { background-color: #E8F5E9 !important; }
    .row-odd td:not(.col-sticky) { background-color: #FFFDE7 !important; }
    </style>
    """

    html = css + '<div class="table-container"><table class="custom-table"><thead><tr>'

    for idx, col in enumerate(df.columns):
        sticky_class = ' class="col-sticky"' if idx == 0 else ""
        clean_col = str(col).replace(" ($)", "").replace("$", "")
        header_text = (
            clean_col.replace(" ", "<br>") if len(clean_col) > 10 else clean_col
        )
        html += f"<th{sticky_class}>{header_text}</th>"

    html += "</tr></thead><tbody>"

    for row_idx, row in df.iterrows():
        row_class = "row-even" if row_idx % 2 == 0 else "row-odd"
        html += f'<tr class="{row_class}">'
        for col_idx, val in enumerate(row):
            sticky_class = ' class="col-sticky"' if col_idx == 0 else ""
            if col_idx == 0:
                formatted_val = str(val)
            elif isinstance(val, (int, float)):
                col_name = str(df.columns[col_idx])
                if (
                    "Total" in col_name
                    or "Día" in col_name
                    or "Transferido" in col_name
                    or "Comprado" in col_name
                ):
                    formatted_val = f"${val:,.2f}"
                else:
                    formatted_val = f"{int(val):,}" if val == int(val) else f"{val:,}"
            else:
                formatted_val = str(val)
            html += f"<td{sticky_class}>{formatted_val}</td>"
        html += "</tr>"

    html += "</tbody></table></div>"
    return html


def render_kpi_card(titulo, valor_str):
    return f"""
    <div style="
        background-color: #0F172A;
        border: 2px solid #FFEB3B;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
        margin-bottom: 12px;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.3);
    ">
        <div style="color: #FFEB3B; font-size: 13px; font-weight: 600; margin-bottom: 4px;">{titulo}</div>
        <div style="color: #FFFFFF; font-size: 20px; font-weight: bold;">{valor_str}</div>
    </div>
    """


tab1, tab2, tab3 = st.tabs(
    ["Retiros por Año", "Transferencias Interbancarias", "Compras por Internet"]
)

with tab1:
    st.html(render_custom_table(tabla_anos))
    st.html(render_kpi_card("Último Retiro (Fecha y Valor)", txt_ultimo_retiro))

with tab2:
    st.html(render_custom_table(tabla_trans))
    st.html(
        render_kpi_card(
            "Última Transferencia (Fecha y Valor)", txt_ultima_trans
        )
    )

with tab3:
    st.html(render_custom_table(tabla_compras))

# Sección de KPIs debajo de las tablas
st.markdown("---")
st.subheader("Indicadores Clave (KPIs)")

filtro_ano = st.selectbox(
    "Filtrar por Año:",
    anos_disponibles,
    index=0
)

if filtro_ano == "Todos":
    total_kpi_retiros = df_retiros["Valor"].sum() if not df_retiros.empty else 0.0
    if not df_retiros.empty:
        min_fecha = df_retiros["Fecha_dt"].min()
        max_fecha = df_retiros["Fecha_dt"].max()
        dias_totales_rango = (
            (max_fecha - min_fecha).days
            if pd.notnull(min_fecha) and pd.notnull(max_fecha)
            else 1
        )
        kpi_retiro_dia = total_kpi_retiros / (
            dias_totales_rango if dias_totales_rango > 0 else 1
        )
    else:
        kpi_retiro_dia = 0.0

    total_kpi_trans = (
        df_trans_fechas["Valor"].sum() if not df_trans_fechas.empty else 0.0
    )
    total_kpi_compras = (
        df_compras["Valor"].sum() if not df_compras.empty else 0.0
    )
    total_kpi_swift = df_swift["Valor"].sum() if not df_swift.empty else 0.0

    lbl_total_retiros = "Total Retiros (Todos los Años)"
    lbl_retiro_dia = "Retiro / Día (Todos los Años)"
    lbl_trans = "Total Transferencias"
    lbl_compras = "Total Compras por Internet"
    lbl_swift = "Total Swift"
else:
    ano_sel = int(filtro_ano)

    if not df_retiros.empty and "Año" in df_retiros.columns:
        df_retiros_f = df_retiros[df_retiros["Año"] == ano_sel]
        total_kpi_retiros = df_retiros_f["Valor"].sum()
        kpi_retiro_dia = total_kpi_retiros / 365
    else:
        total_kpi_retiros = 0.0
        kpi_retiro_dia = 0.0

    if not df_trans_fechas.empty and "Año" in df_trans_fechas.columns:
        total_kpi_trans = df_trans_fechas[df_trans_fechas["Año"] == ano_sel][
            "Valor"
        ].sum()
    else:
        total_kpi_trans = 0.0

    if not df_compras.empty and "Año" in df_compras.columns:
        total_kpi_compras = df_compras[df_compras["Año"] == ano_sel][
            "Valor"
        ].sum()
    else:
        total_kpi_compras = 0.0

    if not df_swift.empty and "Año" in df_swift.columns:
        total_kpi_swift = df_swift[df_swift["Año"] == ano_sel]["Valor"].sum()
    else:
        total_kpi_swift = 0.0

    lbl_total_retiros = f"Total Retiros ({filtro_ano})"
    lbl_retiro_dia = f"Retiro / Día ({filtro_ano})"
    lbl_trans = f"Total Transferencias ({filtro_ano})"
    lbl_compras = f"Total Compras por Internet ({filtro_ano})"
    lbl_swift = f"Total Swift ({filtro_ano})"

col1, col2 = st.columns(2)

with col1:
    st.html(
        render_kpi_card(
            lbl_total_retiros, f"${total_kpi_retiros:,.2f}"
        )
    )
    st.html(
        render_kpi_card(
            lbl_retiro_dia, f"${kpi_retiro_dia:,.2f}"
        )
    )
    st.html(
        render_kpi_card(lbl_compras, f"${total_kpi_compras:,.2f}")
    )

with col2:
    st.html(
        render_kpi_card(lbl_trans, f"${total_kpi_trans:,.2f}")
    )
    st.html(render_kpi_card(lbl_swift, f"${total_kpi_swift:,.2f}"))

if __name__ == "__main__":
    if "streamlit" not in sys.argv[0]:
        os.system(f'streamlit run "{__file__}" --server.port 8501')