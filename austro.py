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
def cargar_datos(url):
  return pd.read_excel(url, sheet_name="Retiros")


df_raw = cargar_datos(EXCEL_URL)

df_retiros = df_raw[["Fecha", "Valor"]].dropna().copy()
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
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .custom-table {
        width: max-content;
        border-collapse: separate;
        border-spacing: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 14px;
    }
    .custom-table th {
        position: sticky !important;
        top: 0 !important;
        z-index: 20 !important;
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        text-align: center !important;
        padding: 10px 14px;
        font-weight: 600;
        white-space: nowrap;
        border-bottom: 2px solid #94A3B8;
        width: max-content !important;
    }
    .custom-table th.col-sticky {
        position: sticky !important;
        left: 0 !important;
        top: 0 !important;
        z-index: 50 !important;
        width: 125px !important;
        min-width: 125px !important;
        box-shadow: 2px 0 5px rgba(0,0,0,0.15);
    }
    .custom-table td {
        position: static !important;
        z-index: auto !important;
        text-align: center !important;
        padding: 10px 14px;
        white-space: nowrap;
        border-bottom: 1px solid #E2E8F0;
        width: max-content !important;
    }
    .custom-table td.col-sticky {
        position: sticky !important;
        left: 0 !important;
        z-index: 30 !important;
        width: 125px !important;
        min-width: 125px !important;
        background-color: #F1F5F9 !important;
        background-clip: padding-box !important;
        font-weight: bold;
        box-shadow: 2px 0 5px rgba(0,0,0,0.15);
        word-wrap: break-word;
        white-space: normal;
    }
    .row-even { background-color: #FFFFFF !important; }
    .row-odd { background-color: #F8FAFC !important; }
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
        if "Total" in col_name or "Día" in col_name:
          formatted_val = f"${val:,.2f}"
        else:
          formatted_val = f"{int(val):,}" if val == int(val) else f"{val:,}"
      else:
        formatted_val = str(val)
      html += f"<td{sticky_class}>{formatted_val}</td>"
    html += "</tr>"

  html += "</tbody></table></div>"
  return html


st.subheader("Retiros por Año")
st.html(render_custom_table(tabla_anos))

if __name__ == "__main__":
  if "streamlit" not in sys.argv[0]:
    os.system(f'streamlit run "{__file__}" --server.port 8501')