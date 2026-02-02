import streamlit as st
from supabase_client import supabase
import bcrypt
from datetime import datetime
from fpdf import FPDF
import os
from email.message import EmailMessage
import smtplib

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
# EMAIL
# ==========================
EMAIL_EXPEDITEUR = os.getenv("EMAIL_EXPEDITEUR")
EMAIL_PASSWORD = os.getenv("NOSENIX_EMAIL_PASSWORD")

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
# SESSION STATE
# ==========================
defaults = {
    "logged": False,
    "user_id": None,
    "nom_complet": None,
    "is_admin": False,
    "page": "login"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

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
        # Vérifier si email existe
        res = supabase.table("clients").select("*").eq("email", email).execute()
        if res.data:
            st.error("Email déjà utilisé")
        elif password != confirm:
            st.error("Les mots de passe ne correspondent pas")
        elif not all([prenom, nom, email, telephone, password]):
            st.error("Tous les champs sont obligatoires")
        else:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            insert = supabase.table("clients").insert({
                "prenom": prenom,
                "nom": nom,
                "email": email,
                "telephone": telephone,
                "password": hashed,
                "is_admin": False
            }).execute()
            st.success("Compte créé avec succès 🎉")
            envoyer_email_confirmation(email, f"{prenom} {nom}")
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
        res = supabase.table("clients").select("*").eq("email", email).execute()
        if not res.data:
            st.error("Email inconnu")
        else:
            user = res.data[0]
            if bcrypt.checkpw(password.encode(), user["password"].encode()):
                st.session_state.logged = True
                st.session_state.user_id = user["id"]
                st.session_state.nom_complet = f"{user['prenom']} {user['nom']}"
                st.session_state.is_admin = user["is_admin"]
                st.experimental_rerun()
            else:
                st.error("Mot de passe incorrect")

# ==========================
# FACTURE PDF
# ==========================
def generate_facture_pdf(vente, produit):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "FACTURE NOSENIX", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Client : {st.session_state.nom_complet}", ln=True)
    pdf.cell(0, 8, f"Produit : {produit['produit']}", ln=True)
    pdf.cell(0, 8, f"Quantité : {vente['quantite']}", ln=True)
    pdf.cell(0, 8, f"Prix unitaire : {vente['prix_unitaire']}", ln=True)
    pdf.cell(0, 8, f"Total : {vente['total']}", ln=True)
    pdf.cell(0, 8, f"Profit : {vente['profit']}", ln=True)
    filename = f"facture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

# ==========================
# DASHBOARD CLIENT
# ==========================
if st.session_state.logged and not st.session_state.is_admin:
    st.header(f"👤 {st.session_state.nom_complet}")
    st.subheader("📦 Mes Produits")

    # Ajouter produit
    with st.expander("➕ Ajouter un produit"):
        produit_name = st.text_input("Produit")
        description = st.text_area("Description")
        stock = st.number_input("Stock", min_value=0)
        prix_achat = st.number_input("Prix achat", min_value=0.0)
        prix_revient = st.number_input("Prix revient", min_value=0.0)
        prix_vente = st.number_input("Prix vente", min_value=0.0)
        if st.button("Enregistrer le produit"):
            supabase.table("produits").insert({
                "client_id": st.session_state.user_id,
                "produit": produit_name,
                "description": description,
                "stock": stock,
                "prix_achat": prix_achat,
                "prix_revient": prix_revient,
                "prix_vente": prix_vente
            }).execute()
            st.success("Produit enregistré")

    # Afficher produits
    res = supabase.table("produits").select("*").eq("client_id", st.session_state.user_id).execute()
    st.dataframe(res.data)

    # Ajouter vente
    st.subheader("💰 Enregistrer une vente")
    produits = res.data
    if produits:
        produit_choice = st.selectbox("Choisir un produit", [p["produit"] for p in produits])
        quantite = st.number_input("Quantité vendue", min_value=1)
        produit_selected = next(p for p in produits if p["produit"] == produit_choice)
        prix_unitaire = st.number_input("Prix unitaire", value=float(produit_selected["prix_vente"]))
        if st.button("Enregistrer la vente"):
            total = prix_unitaire * quantite
            profit = total - (produit_selected["prix_revient"] * quantite)
            vente = supabase.table("ventes").insert({
                "client_id": st.session_state.user_id,
                "produit_id": produit_selected["id"],
                "quantite": quantite,
                "prix_unitaire": prix_unitaire,
                "total": total,
                "profit": profit
            }).execute()
            filename = generate_facture_pdf({"quantite": quantite, "prix_unitaire": prix_unitaire, "total": total, "profit": profit}, produit_selected)
            st.success(f"Vente enregistrée ✅ Facture générée : {filename}")

# ==========================
# DASHBOARD ADMIN
# ==========================
if st.session_state.logged and st.session_state.is_admin:
    st.header("👑 Administration")
    st.subheader("Clients")
    clients = supabase.table("clients").select("*").execute()
    st.dataframe(clients.data)
    st.subheader("Ventes")
    ventes = supabase.table("ventes").select("*").execute()
    st.dataframe(ventes.data)
