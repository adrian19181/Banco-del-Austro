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

# 1. Retiros por Año
df_raw_retiros = obtener_hoja(todas_las_hojas, "Retiros")
df_retiros = df_raw_retiros[["Fecha", "Valor"]].dropna().copy()
df_retiros["Fecha_dt"] = pd.to_datetime(
    df_retiros["Fecha"], format="%d/%m/%Y", dayfirst=True, errors="coerce"
)
df_retiros = df_retiros.dropna(subset=["Fecha_dt"]).sort_values("Fecha_dt")
df_retiros["Año"] = df_retiros["Fecha_dt"].dt.year

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
df_trans = df_raw_trans[["Institución", "Valor"]].dropna().copy()
df_trans.loc[
    df_trans["Institución"].str.contains(
        "JARDIN AZUAYO|Jardín Azuayo", case=False, na=False
    ),
    "Institución",
] = "Jardin Azuayo"

tabla_trans = (
    df_trans.groupby("Institución")["Valor"]
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

# 3. Compras por Internet (Extracción directa Columna C y Columna B)
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
    elif any(k in desc_str for k in ["TRANSEXPRES", "LAARBOX", "FLETE", "EXPRESSWEB", "TRANS EXPRESS"]):
        return "Flete Laarbox"
    elif "FARMASOL" in desc_str:
        return "Farmasol"
    else:
        return desc_str.strip()

if not df_raw_compras.empty and "Descripción" in df_raw_compras.columns and "Valor" in df_raw_compras.columns:
    df_compras = df_raw_compras[["Descripción", "Valor"]].dropna().copy()
    df_compras["Establecimiento"] = df_compras["Descripción"].apply(categorizar_descripcion)
    
    df_compras["Valor"] = pd.to_numeric(df_compras["Valor"], errors="coerce")
    df_compras = df_compras.dropna(subset=["Valor"])

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

tab1, tab2, tab3 = st.tabs(
    ["Retiros por Año", "Transferencias Interbancarias", "Compras por Internet"]
)

with tab1:
    st.html(render_custom_table(tabla_anos))

with tab2:
    st.html(render_custom_table(tabla_trans))

with tab3:
    st.html(render_custom_table(tabla_compras))

if __name__ == "__main__":
    if "streamlit" not in sys.argv[0]:
        os.system(f'streamlit run "{__file__}" --server.port 8501')