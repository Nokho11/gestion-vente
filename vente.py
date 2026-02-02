import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="NOSENIX - Gestion des Ventes", layout="wide")
st.title("NOSENIX - Gestion des Ventes")

# -----------------------------
# Initialisation des données
# -----------------------------
if "produits" not in st.session_state:
    st.session_state.produits = pd.DataFrame({
        "Produit": ["Produit 1","Produit 2","Produit 3"],
        "Prix": [1000,1500,2000],
        "Stock": [50,30,20]
    })

if "ventes" not in st.session_state:
    st.session_state.ventes = pd.DataFrame(columns=["Produit","Quantité","Total","Client"])

if "clients" not in st.session_state:
    st.session_state.clients = pd.DataFrame({
        "Nom": ["Client A","Client B","Client C","Client D"],
        "Téléphone": ["77xxxxxx","77xxxxxx","77xxxxxx","77xxxxxx"],
        "Email": ["clientA@email.com","clientB@email.com","clientC@email.com","clientD@email.com"],
        "Adresse": ["Dakar","Thiès","Saint-Louis","Ziguinchor"]
    })

# -----------------------------
# Ajouter une vente
# -----------------------------
st.header("Ajouter une vente")

col1, col2, col3 = st.columns(3)
with col1:
    client = st.selectbox("Client", st.session_state.clients["Nom"])
with col2:
    produit = st.selectbox("Produit", st.session_state.produits["Produit"])
with col3:
    quantite = st.number_input("Quantité", min_value=1, max_value=100, value=1)

if st.button("Ajouter la vente"):
    prix = st.session_state.produits.loc[st.session_state.produits["Produit"]==produit, "Prix"].values[0]
    stock_dispo = st.session_state.produits.loc[st.session_state.produits["Produit"]==produit, "Stock"].values[0]
    if quantite > stock_dispo:
        st.error(f"Stock insuffisant! Stock disponible : {stock_dispo}")
    else:
        total = prix * quantite
        new_row = {"Produit": produit, "Quantité": quantite, "Total": total, "Client": client}
        st.session_state.ventes = pd.concat([st.session_state.ventes, pd.DataFrame([new_row])], ignore_index=True)
        st.session_state.produits.loc[st.session_state.produits["Produit"]==produit, "Stock"] -= quantite
        st.success(f"Vente ajoutée : {quantite} x {produit} pour {client} (Total {total})")

# -----------------------------
# Affichage des données
# -----------------------------
st.header("Stock actuel")
st.dataframe(st.session_state.produits)

st.header("Ventes enregistrées")
st.dataframe(st.session_state.ventes)

# -----------------------------
# Dashboard / Indicateurs
# -----------------------------
st.header("Tableau de bord")

if not st.session_state.ventes.empty:
    total_ventes = st.session_state.ventes["Total"].sum()
    top_produit = st.session_state.ventes.groupby("Produit")["Quantité"].sum().idxmax()
    top_client = st.session_state.ventes.groupby("Client")["Quantité"].sum().idxmax()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Ventes", f"{total_ventes}")
    col2.metric("Top Produit", top_produit)
    col3.metric("Top Client", top_client)

    # Graphiques
    st.subheader("Ventes par produit")
    st.bar_chart(st.session_state.ventes.groupby("Produit")["Total"].sum())

    st.subheader("Ventes par client")
    st.bar_chart(st.session_state.ventes.groupby("Client")["Total"].sum())

    st.subheader("Répartition des ventes par produit")
    st.pyplot(
        pd.DataFrame(st.session_state.ventes.groupby("Produit")["Total"].sum()).plot.pie(y="Total", autopct="%1.1f%%", legend=False, figsize=(5,5)).figure
    )

# -----------------------------
# Export Excel
# -----------------------------
st.header("Exporter les données")

def to_excel(df_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    processed_data = output.getvalue()
    return processed_data

if st.button("Exporter Excel"):
    df_dict = {
        "Produits": st.session_state.produits,
        "Ventes": st.session_state.ventes,
        "Clients": st.session_state.clients
    }
    excel_data = to_excel(df_dict)
    st.download_button(label="Télécharger Excel", data=excel_data, file_name="NOSENIX_Ventes.xlsx", mime="application/vnd.ms-excel")
