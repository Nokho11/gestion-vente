import streamlit as st
import pandas as pd
import bcrypt
import secrets
import os
from io import BytesIO
from datetime import date

st.set_page_config(page_title="NOSENIX – Gestion des Ventes", layout="wide")
st.title("💼 NOSENIX – Gestion des Ventes")

# =============================
# FICHIERS
# =============================
CLIENTS_FILE = "clients.csv"
VENTES_FILE = "ventes.csv"

# =============================
# INITIALISATION
# =============================
if not os.path.exists(CLIENTS_FILE):
    pd.DataFrame(columns=["nom", "email", "password"]).to_csv(CLIENTS_FILE, index=False)

if not os.path.exists(VENTES_FILE):
    pd.DataFrame(columns=["date", "client", "produit", "quantite", "prix"]).to_csv(VENTES_FILE, index=False)

clients_df = pd.read_csv(CLIENTS_FILE)
ventes_df = pd.read_csv(VENTES_FILE)

# =============================
# SESSION
# =============================
if "logged" not in st.session_state:
    st.session_state.logged = False
    st.session_state.client = None

# =============================
# SIDEBAR
# =============================
st.sidebar.title("🔐 Espace Client")

if not st.session_state.logged:
    action = st.sidebar.radio("Action", ["Connexion", "Créer un compte"])
else:
    action = "Dashboard"

# =============================
# CREATION COMPTE
# =============================
if action == "Créer un compte":
    st.subheader("Créer un compte client")

    nom = st.text_input("Nom")
    email = st.text_input("Email")

    if st.button("Créer le compte"):
        if email in clients_df["email"].values:
            st.error("Email déjà utilisé")
        else:
            password = secrets.token_urlsafe(6)
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

            new_client = pd.DataFrame([{
                "nom": nom,
                "email": email,
                "password": hashed
            }])

            clients_df = pd.concat([clients_df, new_client], ignore_index=True)
            clients_df.to_csv(CLIENTS_FILE, index=False)

            st.success("Compte créé avec succès")
            st.info(f"Mot de passe : {password}")
            st.warning("Conservez ce mot de passe")

# =============================
# CONNEXION
# =============================
if action == "Connexion":
    st.subheader("Connexion")

    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        user = clients_df[clients_df["email"] == email]

        if user.empty:
            st.error("Email inconnu")
        else:
            hashed = user.iloc[0]["password"].encode()
            if bcrypt.checkpw(password.encode(), hashed):
                st.session_state.logged = True
                st.session_state.client = user.iloc[0]["nom"]
                st.success(f"Bienvenue {st.session_state.client}")
                st.rerun()
            else:
                st.error("Mot de passe incorrect")

# =============================
# DASHBOARD CLIENT
# =============================
if st.session_state.logged:
    st.sidebar.success(st.session_state.client)
    if st.sidebar.button("Se déconnecter"):
        st.session_state.logged = False
        st.session_state.client = None
        st.rerun()

    st.header("➕ Ajouter une vente")

    col1, col2, col3 = st.columns(3)
    with col1:
        produit = st.text_input("Produit / Service")
    with col2:
        quantite = st.number_input("Quantité", min_value=1, step=1)
    with col3:
        prix = st.number_input("Prix unitaire (FCFA)", min_value=0)

    if st.button("Ajouter la vente"):
        new_sale = pd.DataFrame([{
            "date": date.today(),
            "client": st.session_state.client,
            "produit": produit,
            "quantite": quantite,
            "prix": prix
        }])

        ventes_df = pd.concat([ventes_df, new_sale], ignore_index=True)
        ventes_df.to_csv(VENTES_FILE, index=False)
        st.success("Vente ajoutée")

    # =============================
    # MES VENTES
    # =============================
    st.header("📊 Mes ventes")
    my_sales = ventes_df[ventes_df["client"] == st.session_state.client]

    st.dataframe(my_sales)

    # =============================
    # KPIs
    # =============================
    if not my_sales.empty:
        ca = (my_sales["quantite"] * my_sales["prix"]).sum()
        top_produit = my_sales.groupby("produit")["quantite"].sum().idxmax()

        col1, col2 = st.columns(2)
        col1.metric("Chiffre d'affaires", f"{ca} FCFA")
        col2.metric("Produit le plus vendu", top_produit)

    # =============================
    # EXPORT EXCEL
    # =============================
    st.header("📥 Export Excel")

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        my_sales.to_excel(writer, index=False, sheet_name="Ventes")

    st.download_button(
        "Télécharger mes ventes",
        data=buffer.getvalue(),
        file_name="mes_ventes_nosenix.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
