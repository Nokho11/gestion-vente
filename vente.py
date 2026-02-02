import streamlit as st
import pandas as pd
import bcrypt
import os
import smtplib
from datetime import date
from pathlib import Path
from email.message import EmailMessage
from fpdf import FPDF

# ==========================
# CONFIGURATION STREAMLIT
# ==========================
st.set_page_config(
    page_title="NOSENIX – Gestion des Ventes",
    layout="wide",
    page_icon="💼"
)

st.title("💼 NOSENIX – Gestion des Ventes")
st.markdown("---")

# ==========================
# CONFIG EMAIL (SECURISÉ)
# ==========================
EMAIL_EXPEDITEUR = "nosenix11@gmail.com"
EMAIL_PASSWORD = os.getenv("47674968")

# ==========================
# FICHIERS & DOSSIERS
# ==========================
CLIENTS_FILE = "clients.csv"
PRODUITS_FILE = "produits.csv"
VENTES_FILE = "ventes.csv"

FACTURES_DIR = Path("factures")
FACTURES_DIR.mkdir(exist_ok=True)

# ==========================
# INITIALISATION CSV
# ==========================
fichiers = [
    (CLIENTS_FILE, ["prenom", "nom", "email", "telephone", "password", "is_admin"]),
    (PRODUITS_FILE, ["client_email", "produit", "description", "stock", "prix_achat", "prix_revient"]),
    (VENTES_FILE, ["client_email", "client_name", "produit", "quantite", "prix_unitaire", "total", "profit", "date"])
]

for fichier, colonnes in fichiers:
    if not os.path.exists(fichier):
        pd.DataFrame(columns=colonnes).to_csv(fichier, index=False)

clients_df = pd.read_csv(CLIENTS_FILE)
produits_df = pd.read_csv(PRODUITS_FILE)
ventes_df = pd.read_csv(VENTES_FILE)

# ==========================
# SESSION STATE
# ==========================
defaults = {
    "logged": False,
    "email": None,
    "nom_complet": None,
    "is_admin": False,
    "page": "login"
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================
# EMAIL DE CONFIRMATION
# ==========================
def envoyer_email_confirmation(destinataire, nom_complet):
    if EMAIL_PASSWORD is None:
        st.warning("⚠️ Email non envoyé (mot de passe email non configuré)")
        return

    msg = EmailMessage()
    msg["Subject"] = "Bienvenue chez NOSENIX 🎉"
    msg["From"] = EMAIL_EXPEDITEUR
    msg["To"] = destinataire

    msg.set_content(f"""
Bonjour {nom_complet},

Votre compte NOSENIX a été créé avec succès ✅

Vous pouvez désormais :
- Gérer vos produits
- Enregistrer vos ventes
- Générer vos factures

Merci de votre confiance.
NOSENIX 💼
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_EXPEDITEUR, EMAIL_PASSWORD)
        server.send_message(msg)

# ==========================
# ACCUEIL
# ==========================
if not st.session_state.logged:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔐 Connexion", use_container_width=True):
            st.session_state.page = "login"
    with col2:
        if st.button("📝 Inscription", use_container_width=True):
            st.session_state.page = "register"

    st.markdown("---")

# ==========================
# INSCRIPTION
# ==========================
if not st.session_state.logged and st.session_state.page == "register":
    st.subheader("📝 Créer un compte client")

    prenom = st.text_input("Prénom")
    nom = st.text_input("Nom")
    email = st.text_input("Email")
    telephone = st.text_input("Téléphone")
    password = st.text_input("Mot de passe", type="password")
    confirm = st.text_input("Confirmer le mot de passe", type="password")

    if st.button("Créer le compte", use_container_width=True):
        if email in clients_df["email"].values:
            st.error("Email déjà utilisé")
        elif password != confirm:
            st.error("Les mots de passe ne correspondent pas")
        elif not all([prenom, nom, email, telephone, password]):
            st.error("Tous les champs sont obligatoires")
        else:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            clients_df.loc[len(clients_df)] = [prenom, nom, email, telephone, hashed, False]
            clients_df.to_csv(CLIENTS_FILE, index=False)

            envoyer_email_confirmation(email, f"{prenom} {nom}")

            st.success("Compte créé avec succès 🎉")
            st.session_state.page = "login"
            st.experimental_rerun()

# ==========================
# CONNEXION
# ==========================
if not st.session_state.logged and st.session_state.page == "login":
    st.subheader("🔐 Connexion")

    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter", use_container_width=True):
        user = clients_df[clients_df["email"] == email]

        if user.empty:
            st.error("Email inconnu")
        elif bcrypt.checkpw(password.encode(), user.iloc[0]["password"].encode()):
            st.session_state.logged = True
            st.session_state.email = email
            st.session_state.nom_complet = f"{user.iloc[0]['prenom']} {user.iloc[0]['nom']}"
            st.session_state.is_admin = bool(user.iloc[0]["is_admin"])
            st.experimental_rerun()
        else:
            st.error("Mot de passe incorrect")

# ==========================
# FACTURE PDF
# ==========================
def generate_facture_pdf(vente):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "FACTURE NOSENIX", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    for col in vente.columns:
        pdf.cell(0, 8, f"{col} : {vente[col].values[0]}", ln=True)

    filename = FACTURES_DIR / f"facture_{date.today()}.pdf"
    pdf.output(str(filename))
    return filename

# ==========================
# DASHBOARD CLIENT
# ==========================
if st.session_state.logged and not st.session_state.is_admin:
    st.header(f"👤 {st.session_state.nom_complet}")

    st.subheader("📦 Mes Produits")

    with st.expander("➕ Ajouter un produit"):
        produit = st.text_input("Produit")
        description = st.text_area("Description")
        stock = st.number_input("Stock", min_value=0)
        prix_achat = st.number_input("Prix achat", min_value=0.0)
        prix_revient = st.number_input("Prix revient", min_value=0.0)

        if st.button("Enregistrer le produit"):
            produits_df.loc[len(produits_df)] = [
                st.session_state.email,
                produit,
                description,
                stock,
                prix_achat,
                prix_revient
            ]
            produits_df.to_csv(PRODUITS_FILE, index=False)
            st.success("Produit enregistré")

    st.dataframe(produits_df[produits_df["client_email"] == st.session_state.email])

# ==========================
# DASHBOARD ADMIN
# ==========================
if st.session_state.logged and st.session_state.is_admin:
    st.header("👑 Administration")
    st.subheader("Clients")
    st.dataframe(clients_df)
    st.subheader("Ventes")
    st.dataframe(ventes_df)
