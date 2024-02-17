# Question possible grand orale :
# Comment lier plusieurs langages de programmation (intéret/utilité par exemple)
# Comment crée ou gérer un bdd et comment tout y stocker dedans (comme pour sfx ou à grande échelle/monde professionnel)

from functools import wraps
from flask import Flask, flash, redirect, render_template, request, url_for, session, abort, make_response, Response, g, send_file, send_from_directory
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from table_bdd import create_engine, Utilisateur, Inscriptions, Ateliers, Cours, Professeurs, Historiques
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment
from jinja2.ext import loopcontrols
import smtplib
import os
import sqlite3
import random
import hashlib
import csv
import time
import ast

engine = create_engine('sqlite:///database/base_de_donnée_AP.db')
DATABASE = './database/base_de_donnée_AP.db'

app = Flask(__name__)

# Permet d'avoir l'option break pour les boucles for dans les templates
env = app.jinja_env
env.add_extension('jinja2.ext.loopcontrols')

app.secret_key = os.urandom(20)

# crée une protection avec des jetons csrf
CSRFProtect(app)


# Permet la connexion à la bdd pour les différentes fonctions


def get_db():
    """
    Crée la connexion vers la bdd
    Nécessaire avant chaque requête
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db
#################################################


# Fonctions qui permet d'interagir avec la bdd
@app.teardown_appcontext
def close_connection(excetion):
    """
    Ferme la connexion vers la bdd
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def selection(requete, args=(), one=False):
    """
    Exécute une requête auprès de la bdd (après l'avoir créée)
    """
    cur = get_db().execute(requete, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def insertion(requete, args=()):
    """
    Insère des valeurs passées dans la base de donnée
    """
    cur = get_db().execute(requete, args)
    get_db().commit()
    return cur.lastrowid


def suppression(requete, args=()):
    """
    Supprime des valeurs dans la base de donnée
    """
    cur = get_db().execute(requete, args)
    get_db().commit()
    return cur.lastrowid
##################################################

# Fonctions qui permettent de transmettre les données aux différentes pages


def cours_eleves(id, niveau, jour_AP=""):
    """
    Fonction qui renvoie les cours associé au niveau de l'élève et si c'est un seconde, selon son jour de cour
    """
    if jour_AP != "":
        niveau_eleve = selection("SELECT cours.id AS [id_cour],cours.nom,cours.effectif_max, professeurs.nom AS [noms], " +
                                 "ateliers.debut_inscription, ateliers.fin_inscription, " +
                                 "ateliers.id AS [id_atelier], count(inscriptions.eleve) - 1 AS [total] " +
                                 "FROM cours INNER JOIN professeurs ON cours.professeur = professeurs.id " +
                                 "INNER JOIN ateliers ON ateliers.id = cours.atelier " +
                                 "INNER JOIN inscriptions ON cours.id = inscriptions.cour " +
                                 f"WHERE ateliers.niveau={niveau} AND ateliers.jour_AP='{jour_AP}' GROUP BY inscriptions.cour ORDER BY cours.id ")
    else:
        niveau_eleve = selection("""
        SELECT cours.id AS [id_cour],cours.nom,cours.effectif_max, professeurs.nom AS [noms], ateliers.debut_inscription,
        ateliers.fin_inscription, ateliers.id AS [id_atelier], count(inscriptions.eleve) - 1 AS [total]
        FROM cours
        INNER JOIN professeurs ON cours.professeur = professeurs.id
        INNER JOIN ateliers ON ateliers.id = cours.atelier
        INNER JOIN inscriptions ON cours.id = inscriptions.cour
        WHERE ateliers.niveau=? GROUP BY inscriptions.cour ORDER BY cours.id
        """, (niveau,))

    return render_template('pageEleves.html', niveau_eleve=niveau_eleve, id=id)


def donnée_pageCours(scroll_position=""):
    """
    Fonction qui envoie les données nécessaire à la page cour
    Evite de devoir rentrer toutes les commandes sql dans chaque fonction
    """
    professeurs = selection("""
    SELECT id,nom
    FROM professeurs
    WHERE ?
    """, (1,))
    cours = selection("""
    SELECT cours.id,cours.atelier,cours.nom,cours.effectif_max, professeurs.nom AS [noms], ateliers.niveau, ateliers.jour_AP
    FROM cours
    INNER JOIN professeurs ON cours.professeur = professeurs.id
    LEFT JOIN ateliers ON ateliers.id = cours.atelier
    WHERE ? ORDER BY ateliers.niveau, ateliers.date_debut ASC
    """, (1,))
    ateliers_encours = selection("""
    SELECT id,niveau,date_debut,date_fin,debut_inscription,fin_inscription, jour_AP
    FROM ateliers
    WHERE ? ORDER BY niveau ASC
    """, (1,))
    return render_template('pageCours.html', ateliers_encours=ateliers_encours,
                           cours=cours, professeurs=professeurs, scroll_position=scroll_position)


def donnée_pageAteliers(scroll_position=""):
    """
    Fonction qui envoie les données nécessaire à la page ateliers
    Evite de devoir rentrer toutes les commandes sql dans chaque fonction
    """
    ateliers_encours = selection("""
    SELECT id,niveau,date_debut,date_fin,debut_inscription,fin_inscription, jour_AP
    FROM ateliers
    WHERE ? ORDER BY niveau, date_debut ASC
    """, (1,))
    return render_template('pageAteliers.html', ateliers_encours=ateliers_encours, scroll_position=scroll_position)


def donnée_pageInscriptions(recherche_eleve="", infos_eleve="", cours_eleve="", fichier=None, niveau_fichier="", scroll_position=""):
    """
    Fonction qui envoie les données nécessaire à la page inscriptions
    Evite de devoir rentrer toutes les commandes sql dans chaque fonction
    Affiche les fichier excels disponibles en téléchargement selon les ateliers
    ainsi que les personnes inscrites dans les différents cours
    """
    non_inscrits = selection("""
    SELECT personnes.nom, personnes.prenom, personnes.classe
    FROM personnes
    WHERE personnes.id NOT IN (SELECT eleve FROM inscriptions) AND personnes.statut="Elève" ORDER BY personnes.niveau, personnes.classe ASC
    """, ())

    download_file = selection("""
    SELECT DISTINCT niveau, jour_AP
    FROM ateliers
    INNER JOIN cours ON cours.atelier = ateliers.id
    INNER JOIN inscriptions ON cours.id = inscriptions.cour
    WHERE ? AND inscriptions.eleve < 10000 ORDER BY niveau ASC
    """, (1,))

    return render_template('pageInscriptions.html', non_inscrits=non_inscrits, download_file=download_file, recherche_eleve=recherche_eleve,
                           infos_eleve=infos_eleve, cours_eleve=cours_eleve, fichier=fichier, niveau_fichier=niveau_fichier, scroll_position=scroll_position)


def donnée_pageHistoriques(historiques="", recherche_eleve="", infos_eleve=""):
    """
    Fonction qui envoie les données nécessaire à la page historiques
    Evite de devoir rentrer toutes les commandes sql dans chaque fonction
    """

    ateliers_historique = selection("""
    SELECT id,niveau, date_debut, date_fin, jour_AP
    FROM historiques
    WHERE ? ORDER BY id DESC
    """, (1,))

    return render_template('pageHistorique.html', ateliers_historique=ateliers_historique, historiques=historiques,
                           recherche_eleve=recherche_eleve, infos_eleve=infos_eleve)


@app.context_processor
def donnée_fonctionnement_site():
    """
    Permet d'afficher sur le site le nom et prénom de l'utilisateur
    Envoie aussi au site l'id de l'utilisateur pour la modification de son mot de passe
    """
    if 'nom' in session:
        return dict(nom=session['nom'], prenom=session['prenom'], id_utilisateur_mdp=session['id'])
    else:
        return dict(nom="", prenom="", id="")
##################################################

# Fonction pour les templates


def longueur(n):
    """
    Fonction qui permet de donner la longueur d'un element
    """
    return len(n)


def index(liste, n):
    """
    Fonction qui renvoie l'indice d'un element dans une liste
    """
    return liste.index(n)


# On rend disponible aux templates les fonctions
app.jinja_env.globals['longueur'] = longueur
app.jinja_env.globals['index'] = index
##################################################


# Fonctions qui permettent de gérer les accès aux pages
# Test à l'aide des sessions si l'utilisateur est bien connecté et/ou est bien un admin
def login_required(f):
    @wraps(f)
    def connexion(*args, **kwargs):
        if 'logged_in' not in session:
            flash("Vous n'est pas connecté !")
            return render_template('login.html')
        return f(*args, **kwargs)
    return connexion


def admin_required(f):
    @wraps(f)
    def admin(*args, **kwargs):
        if 'statut_admin' not in session:
            return Response(u'Vous n'+"'"+'avez pas les autorisations nécéssaires !', mimetype='text/plain', status=401)
        return f(*args, **kwargs)
    return admin
##################################################

# Modification du mot de passe / mot de passe oublié


@app.route('/modification_mdp', methods=['GET', 'POST'])
@login_required
def modification_mdp():
    """
    Fonction qui permet de modifier son mot de passe
    """
    if request.method == 'GET':
        return render_template('change_mdp.html')
    else:
        id = request.form['id_utilisateur_mdp']
        mdp = request.form['mdp']
        mdp2 = request.form['mdp2']

        if mdp != mdp2:
            flash('Les deux mots de passes ne concordent pas !')
            return render_template('change_mdp.html')
        else:
            mot_de_passe = hashlib.sha256()
            mdp = mdp + "Benoit_Jean_les_meilleurs"
            mot_de_passe.update(mdp.encode())
            mot_de_passe = mot_de_passe.hexdigest()

            insertion(
                f"UPDATE personnes SET mdp='{mot_de_passe}' WHERE id=?", id)

            flash("Votre mot de passe a bien été modifié !")
            return déconnexion()


@app.route('/mdp_oublié', methods=['GET', 'POST'])
def mdp_oublié():
    """
    Permet à l'utilisateur de recevoir un nouveau mot de passe par mail pour pouvoir accéder de nouveau à son espace
    """
    if request.method == 'GET':
        return render_template('mdp_oublié.html')
    else:
        identifiant = request.form['identifiant']
        classe = request.form['classe']
        statut = request.form['statut']
        mail = request.form['mail']

        Session = sessionmaker(bind=engine)
        s = Session()

        id = []

        if statut == "Administrateur":
            if classe == "":
                for user in s.query(Utilisateur).filter(text(f"identifiant='{identifiant}' AND statut='{statut}'")):
                    id.append(user.id)
            else:
                flash("Vérifier vos informations")
                return render_template('mdp_oublié.html')

        else:
            if classe == "":
                flash("Vérifier vos informations")
                return render_template('mdp_oublié.html')
            else:
                for user in s.query(Utilisateur).filter(text(f"identifiant='{identifiant}' AND classe='{classe}' AND statut='{statut}'")):
                    id.append(user.id)

        if id == [] or len(id) > 1:
            flash("Vérifier vos informations")
            return render_template('mdp_oublié.html')

        else:
            caracteres = "azertyuiopqsdfghjklmwxcvbnAZERTYUIOPQSDFGHJKLMWXCVBN0123456789"
            longueur = 8
            mdp = ""  # Variable mot de passe
            compteur = 0  # Compteur de lettres

            while compteur < longueur:
                # On tire au hasard une lettre
                lettre = caracteres[random.randint(0, len(caracteres)-1)]
                mdp += lettre  # On ajoute la lettre au mot de passe
                compteur += 1  # On incrémente le compteur de lettres

            Fromadd = "bmaurice@s-fx.fr"
            Toadd = mail  # Spécification des destinataires

            message = MIMEMultipart()  # Création de l'objet "message"
            message['From'] = Fromadd  # Spécification de l'expéditeur
            # Attache du destinataire à l'objet "message"
            message['To'] = Toadd

            # Spécification de l'objet de votre mail
            message['Subject'] = "Récupération de votre mot de passe ( Mail automatique )"
            # Attache du message à l'objet "message", et encodage en UTF-8
            msg = f"Voici votre nouveau mot de passe, connectez vous avec celui-ci et modifier le si vous le souhaitez : {mdp}"
            message.attach(MIMEText(msg.encode('utf-8'), 'plain', 'utf-8'))

            # Connexion au serveur sortant (en précisant son nom et son port)
            serveur = smtplib.SMTP('smtp.office365.com', 587)
            serveur.starttls()  # Spécification de la sécurisation
            # Authentification + le mot de passe de l'envoyeur
            serveur.login(Fromadd, "**********") # A remplacer avec le mot de passe du compte
            # Conversion de l'objet "message" en chaine de caractère et encodage en UTF-8
            texte = message.as_string().encode('utf-8')

            serveur.sendmail(Fromadd, Toadd, texte)  # Envoi du mail
            serveur.quit()  # Déconnexion du serveur

            mot_de_passe = hashlib.sha256()
            mdp = mdp + "Benoit_Jean_les_meilleurs"
            mot_de_passe.update(mdp.encode())
            mot_de_passe = mot_de_passe.hexdigest()

            insertion(
                f"UPDATE personnes SET mdp='{mot_de_passe}' WHERE id=?", id)

            flash("Votre nouveau mot de passe vient de vous être envoyé !")
            return déconnexion()


##################################################


# Fonction qui gère l'arrivée et la connexion de l'utilisateur


@ app.route('/')
def home():
    """
    Fonction qui Récupère les cookies sur le navigateur de l'utilisateur si il y en a
    Si les statuts correspondent, alors l'utilisateur n'a pas besoin de rentrer de nouveau ses codes
    Et est directement redirigé vers la bonne page
    """
    id = request.cookies.get('id')
    statut = request.cookies.get('statut')
    niveau = request.cookies.get('niveau')

    statut_admin = 'e77033f983beb1125cfa83824358449761f254999fce652e3e740926b9539163'
    statut_eleve = '7e996757f0d502e3e0363bbd5b888fed543ce17f7adca6262e7115c1237c5ca1'

    if id != "" and id != None:
        id = int(id)

        session['nom'] = True
        session['prenom'] = True

        Session = sessionmaker(bind=engine)
        s = Session()

        for user in s.query(Utilisateur).filter(text(f"id={id}")):
            session['nom'] = user.nom
            session['prenom'] = user.prenom

        nom = session['nom']
        prenom = session['prenom']

        session['id'] = True
        session['id'] = id

    if statut == statut_admin:
        session['logged_in'] = True
        session['statut_admin'] = True
        return redirect(url_for('acceuil_admin'))
    elif statut == statut_eleve:
        session['logged_in'] = True
        if niveau == "d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35":
            return render_template('Choix_jour_cour.html', id=id, nom=nom, prenom=prenom)
        elif niveau == "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b":
            return cours_eleves(id, 1)
        elif niveau == '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9':
            return cours_eleves(id, 0)
    else:
        return render_template('login.html')


@ app.route('/connexion', methods=['POST'])
def connexion():
    """
    Fonction qui récupère les informations rentrées par l'utilisateur
    Créer une session qui gardera l'utilisateur connecté le temps qu'il est sur le site et pour interagir avec la base de donnée
    Interroge la base de donnée avec les infos donnée par l'utilisateur pour vérifier leur exactitude
    Si elles sont correctes, l'utilisateur est connecté
    Sinon il est refusé
    Avec l'identifiant, on vérifie le statut de l'utilisateur si c'est un administrateur ou autre
    et on le redirige vers la bonne page
    Crée un cookie pour garder l'utilisateur connecté pendant 90 jours à sa demande
    """
    identifiant = str(request.form['identifiant'])
    mot_de_passe = str(request.form['mot_de_passe'])
    cookie_connexion = str(request.form['cookie_connexion'])

    mot_de_passe = mot_de_passe + "Benoit_Jean_les_meilleurs"
    # Hashage du mot de passe rentré par l'utilisateur pour le comparer ensuite avec celui de la bdd qui est hashé
    mdp = hashlib.sha256()
    mdp.update(mot_de_passe.encode())
    mdp = mdp.hexdigest()

    Session = sessionmaker(bind=engine)
    s = Session()

    # Vérifie les infos données par l'utilisateur si elles sont correctes
    connexion = s.query(Utilisateur).filter(Utilisateur.identifiant.in_([identifiant]),
                                            Utilisateur.mdp.in_([mdp]))
    resultat = connexion.first()
    if resultat:
        session['logged_in'] = True
        session['nom'] = True
        session['prenom'] = True
        session['id'] = True
        for user in s.query(Utilisateur).filter(text(f"identifiant='{identifiant}' AND mdp='{mdp}'")):
            session['nom'] = user.nom
            session['prenom'] = user.prenom
            id = user.id
            session['id'] = user.id

        # Test si l'utilisateur est un admin
        statut_personne = s.query(Utilisateur).filter(Utilisateur.identifiant.in_(
            [identifiant]), Utilisateur.mdp.in_([mdp]), Utilisateur.statut.in_(["Administrateur"]))
        statut = statut_personne.first()
        if statut:
            session['statut_admin'] = True
            if cookie_connexion == "True":
                return set_cookie(id, "", "Administrateur")
            else:
                return redirect(url_for('acceuil_admin'))
        else:
            # Test si l'utilisateur est soit un terminal, un première ou seconde
            # Renvoie les cours liés à son niveau
            for niveau in range(3):
                niveaux = s.query(Utilisateur).filter(Utilisateur.identifiant.in_(
                    [identifiant]), Utilisateur.mdp.in_([mdp]), Utilisateur.niveau.in_([niveau]))
                niveau_eleve = niveaux.first()
                if niveau_eleve:
                    if cookie_connexion == "True":
                        return set_cookie(id, niveau, "Elève")
                    else:
                        if niveau == 2:
                            return render_template('Choix_jour_cour.html', id=id)
                        else:
                            return cours_eleves(id, niveau)
    else:
        flash('Mot de passe incorrect !')
        return home()


@ app.route('/deconnexion', methods=['POST'])
def déconnexion():
    """
    Déconnexion du site
    """
    session.pop('logged_in', None)
    session.pop('statut_admin', None)
    session.pop('nom', None)
    session.pop('prenom', None)
    cookie = make_response(render_template('login.html'))
    cookie.set_cookie('niveau', '')
    cookie.set_cookie('statut', '')
    cookie.set_cookie('id', '')
    return cookie


def set_cookie(id="", niveau="", statut=""):
    """
    Fonction qui crée un cookie pour garder l'utilisateur connecté
    Hashage du statut car il était visible et donc un élève aurait pu devenir un admin
    Hashage du niveau car un élève aurait pu changer de niveau
    Garde l'utilisateur connecté pendant 90 jours
    """
    if statut == "Administrateur":
        cookie = make_response(redirect(url_for('acceuil_admin')))
        cookie.set_cookie('statut', 'e77033f983beb1125cfa83824358449761f254999fce652e3e740926b9539163',
                          max_age=3600*24*90)
        cookie.set_cookie('id', str(id), max_age=3600*24*90)
        return cookie
    else:
        if niveau == 2:
            cookie = make_response(render_template(
                'Choix_jour_cour.html', id=id))
            cookie.set_cookie(
                'niveau', 'd4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35', max_age=3600*24*90)
            cookie.set_cookie(
                'statut', '7e996757f0d502e3e0363bbd5b888fed543ce17f7adca6262e7115c1237c5ca1', max_age=3600*24*90)
            cookie.set_cookie('id', str(id), max_age=3600*24*90)
            return cookie
        elif niveau == 1:
            cookie = make_response(cours_eleves(id, niveau))
            cookie.set_cookie(
                'niveau', '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b', max_age=3600*24*90)
            cookie.set_cookie(
                'statut', '7e996757f0d502e3e0363bbd5b888fed543ce17f7adca6262e7115c1237c5ca1', max_age=3600*24*90)
            cookie.set_cookie('id', str(id), max_age=3600*24*90)
            return cookie
        else:
            cookie = make_response(cours_eleves(id, niveau))
            cookie.set_cookie(
                'niveau', '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9', max_age=3600*24*90)
            cookie.set_cookie(
                'statut', '7e996757f0d502e3e0363bbd5b888fed543ce17f7adca6262e7115c1237c5ca1', max_age=3600*24*90)
            cookie.set_cookie('id', str(id), max_age=3600*24*90)
            return cookie


##################################################

# Fonction nécéssaire aux pages administrateurs


@ app.route('/acceuil_admin', methods=['GET', 'POST'])
@ login_required
@ admin_required
def acceuil_admin():
    """
    Affiche la page d'acceuil pour l'administrateur
    """
    return render_template("pageAdmin.html")


@ app.route('/choix_pageAdmin', methods=['POST'])
@ login_required
@ admin_required
def choix_pageAdmin():
    """
    Fonction qui redirige vers la page demandé par l'administrateur
    """
    page = request.form['choix_page_admin']
    if page == "Inscriptions":
        return donnée_pageInscriptions()
    elif page == "Cours":
        return donnée_pageCours()
    elif page == "Ateliers":
        return donnée_pageAteliers()
    elif page == "Historiques":
        return donnée_pageHistoriques()


@ app.route('/création_ateliers', methods=['POST'])
@ login_required
@ admin_required
def création_ateliers():
    """
    Fonction qui créer un atelier
    Elle récupère les valeurs données par l'admin
    Et les insert dans la base de donnée
    Convertion de la date du format 'yyyy-mm-dd' au format 'dd-mm-yyyy', plus simple à lire
    """
    niveau = int(request.form['Niveau'])
    jour_AP = str(request.form['jour_AP'])
    scroll_position = request.form['scroll_position']

    date_debut = datetime.strptime(str(request.form['date_debut']), '%Y-%m-%d')
    date_fin = datetime.strptime(str(request.form['date_fin']), '%Y-%m-%d')
    date_debut_inscription = datetime.strptime(
        str(request.form['debut_inscription']), '%Y-%m-%d')
    date_fin_inscription = datetime.strptime(
        str(request.form['fin_inscription']), '%Y-%m-%d')

    atelier = []
    atelier.append(niveau)
    atelier.append(date_debut.strftime('%d/%m/%Y'))
    atelier.append(date_fin.strftime('%d/%m/%Y'))
    atelier.append(date_debut_inscription.strftime('%d/%m/%Y'))
    atelier.append(date_fin_inscription.strftime('%d/%m/%Y'))
    atelier.append(jour_AP)

    Session = sessionmaker(bind=engine)
    s = Session()
    # On test si il y a déja un atelier avec les mêmes caractéristiques que ceux rentrés par l'utilisateur
    # Si c'est le cas, alors on renvoie un message d'erreur
    for at in s.query(Ateliers).filter(text(f"niveau={atelier[0]} AND date_debut='{atelier[1]}' AND date_fin='{atelier[2]}' AND debut_inscription='{atelier[3]}' AND fin_inscription='{atelier[4]}' AND jour_AP='{atelier[5]}'")):
        if at.id != None:
            flash('Il existe déja un atelier avec les mêmes caractéristiques !')
            return donnée_pageAteliers()

    insertion("""
    INSERT INTO ateliers (niveau,date_debut,date_fin,debut_inscription,fin_inscription,jour_AP)
    VALUES (?,?,?,?,?,?)
    """, atelier)

    return donnée_pageAteliers(scroll_position)


@ app.route('/création_cours', methods=['POST'])
@ login_required
@ admin_required
def création_cours():
    """
    Fonction qui permet de créer un cour
    Récupère les valeurs fournies par l'admin et les inserts dans la bdd
    """
    atelier = int(request.form['id_atelier'])
    nom_cour = str(request.form['nom_cour'])
    professeur = int(request.form['id_professeur'])
    effectif_max = int(request.form['effectif_cour'])
    scroll_position = request.form['scroll_position']

    Session = sessionmaker(bind=engine)
    s = Session()

    # On test si il y a déja un cour avec les mêmes caractéristiques que ceux rentrés par l'utilisateur
    # Si c'est le cas, alors on renvoie un message d'erreur
    for cour in s.query(Cours).filter(text(f"atelier={atelier} AND nom='{nom_cour}' AND professeur={professeur} AND effectif_max={effectif_max}")):
        if cour.id != None:
            flash('Il existe déja un cour avec les mêmes caractéristiques !')
            return donnée_pageCours()

    cour = []
    cour.append(atelier)
    cour.append(nom_cour)
    cour.append(professeur)
    cour.append(effectif_max)

    insertion("""
    INSERT INTO cours (atelier,nom,professeur,effectif_max)
    VALUES (?,?,?,?)
    """, cour)

    # Les lignes suivantes permettent de récupérer l'id du cour précédement crée
    # Et ensuite crée une inscription factice sur ce cour car si il y a aucune inscription,
    # le cour n'est pas affiché et de plus, on crée une valeur aléatoire pour la table élève car
    # si on laisse l'auto-increment de la bdd, elle risque de choisir un id d'un élève

    id_cour = []
    id_cour.append(random.randint(10**8, 10**9))

    for cour in s.query(Cours).filter(text(f"atelier={atelier} AND nom='{nom_cour}' AND professeur={professeur} AND effectif_max={effectif_max}")):
        id_cour.append(cour.id)

    insertion("""
    INSERT INTO inscriptions(eleve,cour)
    VALUES (?,?)
    """, id_cour)
    ###################################################

    return donnée_pageCours(scroll_position)


@ app.route('/suppression_ateliers', methods=['GET'])
@ login_required
@ admin_required
def suppression_ateliers():
    """
    Fonction qui supprime l'atelier voulu par l'admin
    """
    id = request.args['id']

    historique("suppression_atelier", id)

    suppression("""
    DELETE
    FROM ateliers
    WHERE id=?
    """, [id])

    return donnée_pageAteliers()


@ app.route('/suppression_cours', methods=['GET'])
@ login_required
@ admin_required
def suppression_cours():
    """
    Fonction qui supprime le cour voulu par l'admin
    Supprime également les inscriptions lié à ce cour
    """
    id = request.args['id']

    historique("suppression_cour", id)

    suppression("""
    DELETE
    FROM inscriptions
    WHERE cour=?
    """, [id])

    suppression("""
    DELETE
    FROM cours
    WHERE id=?
    """, [id])

    return donnée_pageCours()


@ app.route('/modification_cour', methods=['POST'])
@ login_required
@ admin_required
def mofidication_cour():
    """
    Fonction qui permet de modifier l'ateliers d'un ou plusieurs cours sans à avoir les recrées
    Supprime les inscriptions liées aux cours mis à jour car si l'on met à jour un cour sur un
    nouvel atelier sans le recréer pour qu'il est de nouvelles dates, celui-ci apparaitra
    complet alors qu'il est sur une nouvel session, un nouveau créneau, et que de plus les éleves
    précédement inscrits ne veulent pas forcément être de nouveau dans celui-ci.
    Crée une inscription factice aux cours pour qu'ils soient affichés
    """
    id_atelier = request.form['id_atelier']
    id_cours = request.form['id_cours']
    scroll_position = request.form['scroll_position2']

    cours = id_cours.split(",")

    cours.pop(-1)

    id_C = []

    for elt in cours:
        id_C.append(int(elt))

    historique("modification_cour", id_C)

    for elt in id_C:
        insertion("""
        UPDATE cours
        SET atelier=?
        WHERE id=?
        """, [id_atelier, elt])
        suppression("""
        DELETE FROM inscriptions
        WHERE cour=?
        """, [elt])
        insertion("""
        INSERT INTO inscriptions(eleve,cour)
        VALUES (?,?)
        """, [random.randint(10**8, 10**9), elt])

    return donnée_pageCours(scroll_position)


@ app.route('/recherche_eleve', methods=['POST'])
@ login_required
@ admin_required
def recherche_eleve():
    """
    Focntion qui permet de chercher un élève dans la base de donnée
    """
    prenom_eleve = str(request.form['prenom_eleve'])
    nom_eleve = str(request.form['nom_eleve'])
    scroll_position = request.form['scroll_position']

    recherche_eleve = selection(
        f"SELECT id, nom, prenom, classe FROM personnes WHERE nom LIKE '%{nom_eleve}%' AND prenom LIKE '%{prenom_eleve}%'", )

    return donnée_pageInscriptions(recherche_eleve, "", "", "", "", scroll_position)


@ app.route('/infos_eleve', methods=['GET'])
@ login_required
@ admin_required
def infos_eleve():
    """
    Fonction qui permet d'accéder aux informations d'un élève précisement
    Récupère le cour ou est inscrit l'élève
    Les deux requêtes sql pour récupérer les infos de l'élève sont séparées
    car si l'élève ne s'est pas inscrit, ses données ne sont pas affichées
    """
    id = request.args['id']
    scroll_position = request.args['scroll_position']
    infos_eleve = selection("""
    SELECT personnes.nom, personnes.prenom, personnes.classe
    FROM personnes
    WHERE personnes.id=?
    """, (id,))
    cours_eleve = selection("""
    SELECT cours.nom, professeurs.nom AS [nom_prof], ateliers.niveau, ateliers.jour_AP
    FROM cours
    INNER JOIN inscriptions ON inscriptions.cour = cours.id
    INNER JOIN professeurs ON cours.professeur = professeurs.id
    INNER JOIN ateliers ON cours.atelier = ateliers.id
    WHERE inscriptions.eleve=?
    """, (id,))

    return donnée_pageInscriptions("", infos_eleve, cours_eleve, "", "", scroll_position)


@ app.route('/creation_csv', methods=['GET'])
@ login_required
@ admin_required
def création_csv():
    """
    Fonction qui rentre les inscriptions des cours dans un fichier csv selon le niveau voulu par l'administrateur
    """
    niveau = int(request.args['niveau'])
    if niveau == 2:
        jour_AP = str(request.args['jour'])

    ateliers = []
    id_cours = []
    inscrits = []
    nom_cours = []
    eleves = []
    liste_csv = []

    Session = sessionmaker(bind=engine)
    s = Session()

    # On récupère l'id de l'atelier du niveau voulu et si c'est les inscriptions des secondes, du jour voulu
    if niveau == 2:
        for id_atelier in s.query(Ateliers).filter(text(f"niveau={niveau} AND jour_AP='{jour_AP}'")):
            ateliers.append(id_atelier.id)
    else:
        for id_atelier in s.query(Ateliers).filter(text(f"niveau={niveau}")):
            ateliers.append(id_atelier.id)

    # On récupère tous les cours basés sur cet atelier
    for cour in s.query(Cours).filter(text(f"atelier={ateliers[0]}")):
        id_cours.append(cour.id)

    # On récupère toutes les personnes inscrites pour chaque cour (en ayant enlever la fausse inscription bien sur)
    # On stock cela sous forme d'un couple [id du cour, id de l'élève]
    for i in id_cours:
        for j in s.query(Inscriptions).filter(text(f"cour={i}")):
            if j.eleve < 10_000:
                inscrits.append([j.cour, j.eleve])

    # On récupère les informations sur chaque cour
    # On stock cela sous forme d'une liste [id du cour, nom du cour, nom du professeur]
    # La liste visité permet d'éviter d'avoir plusieurs fois le même cour dans la liste des cours
    visité = []
    for k in inscrits:
        for l in s.query(Cours).filter(text(f"id={k[0]}")):
            for prof in s.query(Professeurs).filter(text(f"id={l.professeur}")):
                if l.nom not in visité:
                    visité.append(l.nom)
                    nom_cours.append([k[0], l.nom, prof.nom])

    # On récupère les informations sur chaque élève inscrit aux differents cours
    # on stock cela sous forme d'une liste [id du cour, nom de l'élève, prénom de l'élève, classe de l'élève]
    for l in inscrits:
        for eleve in s.query(Utilisateur).filter(text(f"id={l[1]}")):
            eleves.append([l[0], eleve.nom, eleve.prenom, eleve.classe])

    # On insert dans la liste liste_csv le cour ainsi que les personnes inscrites à ce cour
    # Liste qui servira pour injecter les données dans le csv
    for m in nom_cours:
        liste_csv.append([m[1], m[2]])
        for n in eleves:
            if m[0] == n[0]:
                liste_csv.append([n[1], n[2], n[3]])
        for i in range(2):
            liste_csv.append(" ")

    if niveau == 0:
        c = csv.writer(open('csv/cour_terminale.csv', 'w', encoding='utf-8'))
        fichier = 'cour_terminale.csv'
        niveau_fichier = "Terminales"
    elif niveau == 1:
        c = csv.writer(open('csv/cour_première.csv', 'w', encoding='utf-8'))
        fichier = 'cour_première.csv'
        niveau_fichier = "Premières"
    else:
        if jour_AP == "Mardi":
            c = csv.writer(
                open('csv/cour_seconde_mardi.csv', 'w', encoding='utf-8'))
            fichier = 'cour_seconde_mardi.csv'
            niveau_fichier = "Secondes le Mardi"
        else:
            c = csv.writer(
                open('csv/cour_seconde_jeudi.csv', 'w', encoding='utf-8'))
            fichier = 'cour_seconde_jeudi.csv'
            niveau_fichier = "Secondes le Jeudi"

    for element in liste_csv:
        c.writerow(element)

    return donnée_pageInscriptions("", "", "", fichier, niveau_fichier)


@ app.route("/get_csv/<path:filename>", methods=['POST'])
@ login_required
@ admin_required
def get_csv(filename):
    """
    Fonction qui envoie le fichier csv à l'administrateur selon le niveau voulu
    """
    return send_from_directory('csv', filename, as_attachment=True)


@app.route('/historique/<appel_fonction>,<id>', methods=['GET', 'POST'])
@ login_required
@ admin_required
def historique(appel_fonction, id):
    """
    Fonction qui permet de garder l'historique des différents ateliers/cours ainsi que leur inscriptions
    Ou de renvoyer l'historique d'un atelier ou d'un élève
    Les données des cours et des inscriptions sont séparées par des points virgules, très peu utilisé en python
    De plus, ces données sont enregistrées sous forme de liste, l'avantage c'est que nous pouvons directement travaillé 
    dessus avec python lorsque nous les récupérons de la bdd directement et aussi, pouvoir s'aider des indices des éléments présent dedans
    """

    Session = sessionmaker(bind=engine)
    s = Session()

    # listes pour la gestion de l'atelier
    cours = []
    atelier = []
    same_atelier = []

    # listes et variables pour la gestion/modification du cour
    inscrits = []
    atelier_cour = []
    infos_cour = []
    infos_atelier_historique = []

    # listes pour l'affichage des infos de l'atelier sélectionné
    historiques = []

    # listes pour les ateliers de l'élève voulu
    ateliers_eleve = []
    historiques_eleve = []
    cours_eleves = []
    inscriptions = []

    if appel_fonction == "suppression_atelier":

        # On récupère d'abord les cours basé sur l'atelier
        for cour in s.query(Cours).filter(text(f'atelier={id}')):
            cours.append(cour.id)

        # On vérifie si il y en a
        # Si il y en a pas, alors on ne le sauvegarde pas
        if cours == []:
            return None
        else:
            # On récupère les infos de l'atelier
            for infos in s.query(Ateliers).filter(text(f'id={id}')):
                atelier.append(infos.id)
                atelier.append(infos.niveau)
                atelier.append(infos.date_debut)
                atelier.append(infos.date_fin)
                atelier.append(infos.debut_inscription)
                atelier.append(infos.fin_inscription)
                atelier.append(infos.jour_AP)

            # On vérifie s'il y a un atelier pareil à celui supprimer dans la table historiques
            for info_atelier in s.query(Historiques).filter(text(f"niveau={atelier[1]} AND date_debut='{atelier[2]}' AND date_fin='{atelier[3]}' AND debut_inscription='{atelier[4]}' AND fin_inscription='{atelier[5]}' AND jour_AP='{atelier[6]}'")):
                same_atelier.append(info_atelier.id)

            # Si ce n'est pas le cas, alors on peut l'inserer
            if same_atelier == []:
                insertion("""
                INSERT INTO historiques (id,niveau,date_debut,date_fin,debut_inscription,fin_inscription,jour_AP)
                VALUES (?,?,?,?,?,?,?)
                """, atelier)

            # Sinon on remplace l'id de l'atelier déja présent par le nouveau
            # S'il reste des cours avec l'id de l'atelier déja présent dans l'historique
            # alors on les met à jour sur le nouvel id, on les faits pointé vers le nouveau
            # Tous les cours avec l'ancien atelier sont mis à jour
            else:
                insertion(
                    f"UPDATE cours SET atelier={atelier[0]} WHERE atelier=?", [same_atelier[0]])
                insertion(
                    f"UPDATE historiques SET id={atelier[0]} WHERE id=?", [same_atelier[0]])

    elif appel_fonction == "suppression_cour":

        # On récupère d'abord les inscriptions
        for inscrit in s.query(Inscriptions).filter(text(f'cour={id}')):
            if inscrit.eleve < 10_000:
                inscrits.append(inscrit.eleve)

        # On vérife s'il y en a
        # S'il n'y en a pas, alors on ne le sauvegarde pas ( aucun interet )
        if inscrits == []:
            return None
        else:

            # On récupère les infos du cour
            for infos in s.query(Cours).filter(text(f'id={id}')):
                for prof in s.query(Professeurs).filter(text(f'id={infos.professeur}')):
                    infos_cour.append(infos.nom)
                    infos_cour.append(prof.nom)
                    id_atelier = infos.atelier

            # On récupère les infos de l'atelier dans la table atelier s'il est présent
            for AT in s.query(Ateliers).filter(text(f'id={id_atelier}')):
                atelier_cour.append(AT.id)
                atelier_cour.append(AT.niveau)
                atelier_cour.append(AT.date_debut)
                atelier_cour.append(AT.date_fin)
                atelier_cour.append(AT.debut_inscription)
                atelier_cour.append(AT.fin_inscription)
                atelier_cour.append(AT.jour_AP)

            # Si la liste est vide, alors c'est qu'il a été supprimer et est donc dans la table historique
            if atelier_cour == []:

                # On récupère les cours déja présent de l'atelier
                for inscription in s.query(Historiques).filter(text(f'id={id_atelier}')):
                    infos_atelier_historique.append(inscription.cours)
                    infos_atelier_historique.append(
                        inscription.inscriptions_cour)

                # On vérifie s'il y en a
                # S'il y en a pas, alors on peut ajouter le cour sans soucis
                if infos_atelier_historique == [None, None]:

                    infos_atelier_historique.pop()
                    infos_atelier_historique.pop()
                    infos_atelier_historique.append(str(infos_cour) + ";")
                    infos_atelier_historique.append(str(inscrits) + ";")

                    insertion(f"UPDATE historiques SET cours=?, inscriptions_cour=? WHERE id=?", [
                              infos_atelier_historique[0], infos_atelier_historique[1], id_atelier])

                # Sinon on ajoute aux cours/inscriptions récupérer les nouvelles données et on réinjecte le tout
                else:

                    infos_atelier_historique[0] = infos_atelier_historique[0] + str(
                        infos_cour) + ";"
                    infos_atelier_historique[1] = infos_atelier_historique[1] + str(
                        inscrits) + ";"

                    insertion(f"UPDATE historiques SET cours=?, inscriptions_cour=? WHERE id=?", [
                              infos_atelier_historique[0], infos_atelier_historique[1], id_atelier])

            # Sinon il faut le créer dans la table historique
            else:

                # On vérifie qu'il n'y a pas un atelier avec les mêmes caractéristiques que celui du cour dans la table historiques
                # Car par exemple on crée un atelier puis on créé des cours dessus et on le supprime puis on recrée un atelier
                # avec les mêmes caractéristiques sauf qu'on supprime d'abord les cours du nouvel atelier et donc cela pourrait crée un doublon
                # au niveau des ateliers
                for info_atelier in s.query(Historiques).filter(text(f"niveau={atelier_cour[1]} AND date_debut='{atelier_cour[2]}' AND date_fin='{atelier_cour[3]}' AND debut_inscription='{atelier_cour[4]}' AND fin_inscription='{atelier_cour[5]}' AND jour_AP='{atelier_cour[6]}'")):
                    infos_atelier_historique.append(info_atelier.id)
                    infos_atelier_historique.append(info_atelier.cours)
                    infos_atelier_historique.append(
                        info_atelier.inscriptions_cour)

                # Si la liste n'est pas vide, alors il y a bien un atelier
                if infos_atelier_historique != []:

                    # S'il y a présence de None dans la liste, c'est qu'il y a un atelier mais sans cour dessus
                    if None in infos_atelier_historique:
                        infos_atelier_historique.pop()
                        infos_atelier_historique.pop()

                    # On vérifie s'il y a déja des cours sur l'atelier ou non
                    # On a récupérer l'id ainsi que les cours s'il y en a
                    # S'il y en a pas, alors seul l'id de l'atelier est présent
                    if len(infos_atelier_historique) > 1:

                        infos_atelier_historique[1] = infos_atelier_historique[1] + str(
                            infos_cour) + ";"
                        infos_atelier_historique[2] = infos_atelier_historique[2] + str(
                            inscrits) + ";"

                        insertion(
                            f"UPDATE historiques SET cours=?, inscriptions_cour=? WHERE id=?", [infos_atelier_historique[1], infos_atelier_historique[2], infos_atelier_historique[0]])

                    else:
                        infos_atelier_historique.append(str(infos_cour) + ";")
                        infos_atelier_historique.append(str(inscrits) + ";")

                        insertion(
                            f"UPDATE historiques SET cours=?, inscriptions_cour=? WHERE id=?", [infos_atelier_historique[1], infos_atelier_historique[2], infos_atelier_historique[0]])

                # Il n'y en a pas donc on peut injecter le nouvel atelier avec les nouveaux cours
                else:
                    atelier_cour.append(str(infos_cour) + ";")
                    atelier_cour.append(str(inscrits) + ";")

                    # Puis on injecte tout cela dans la table historique
                    insertion("""
                    INSERT INTO historiques (id,niveau,date_debut,date_fin,debut_inscription,fin_inscription,jour_AP,cours,inscriptions_cour)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """, atelier_cour)

    elif appel_fonction == "modification_cour":
        # Lorsqu'on modifie l'atelier d'un cour, c'est le même principe que la suppression d'un cour au niveau de l'archivage
        # Et donc on applique la fonction historique, avec comme appel de la fonction suppression_cour, sur chaque cour
        for cour in id:
            historique("suppression_cour", cour)

    elif appel_fonction == 'recherche_atelier':

        # On récupère d'abord les cours et les inscriptions de l'atelier
        for ht in s.query(Historiques).filter(text(f"id={id}")):
            historiques.append(ht.cours)
            historiques.append(ht.inscriptions_cour)

        # On les sépare pour pouvoir travailler sur chacun
        i_historique = historiques.pop()
        c_historique = historiques.pop()

        # On sépare chaques cours/inscriptions entre eux
        cours_historique = c_historique.split(";")
        inscrits_historique = i_historique.split(";")

        # On enlève le dernier ; pour éviter tout problème par la suite
        cours_historique.pop()
        inscrits_historique.pop()

        # On passe les listes du format str au format list pour pouvoir travailler dessus avec les indices
        for i in range(len(cours_historique)):
            cours_historique[i] = ast.literal_eval(cours_historique[i])
            inscrits_historique[i] = ast.literal_eval(inscrits_historique[i])

        # On récupère les infos des élèves
        # A ce stade, la liste des inscrits est composé comme ceci: [[5,6],[9,8],[15,23], etc.. ]
        # On parcours chaque liste dans la liste pour remplacer l'id de l'élève par ses infos
        for j in range(len(inscrits_historique)):
            for k in range(len(inscrits_historique[j])):
                for eleve in s.query(Utilisateur).filter(text(f"id={inscrits_historique[j][k]}")):
                    inscrits_historique[j][k] = [
                        eleve.nom, eleve.prenom, eleve.classe]

        # Puis on regroupe le tout pour ensuite l'envoyer au site
        # On enregistre d'abord les infos du cour puis toutes les inscriptions de celui-ci
        for l in range(len(cours_historique)):
            historiques.append(cours_historique[l])
            for m in range(len(inscrits_historique[l])):
                historiques.append(inscrits_historique[l][m])

        return donnée_pageHistoriques(historiques)

    elif appel_fonction == "recherche_eleve":

        # On renvoie tous les élèves ayant pour nom et prénom ce qu'a rentrer l'utilisateur
        prenom_eleve = str(request.form['prenom'])
        nom_eleve = str(request.form['nom'])

        recherche_eleve = selection(
            f"SELECT id, nom, prenom, classe FROM personnes WHERE nom LIKE '%{nom_eleve}%' AND prenom LIKE '%{prenom_eleve}%' ORDER BY niveau,classe ASC", )

        return donnée_pageHistoriques("", recherche_eleve, "")

    elif appel_fonction == "eleve":

        # On récupère d'abord le niveau de l'élève
        for eleve in s.query(Utilisateur).filter(text(f'id={id}')):
            niveau = eleve.niveau

        # Puis on récupère tous les ateliers sur son niveau
        for at in s.query(Historiques).filter(text(f'niveau={niveau} AND cours IS NOT NULL ORDER BY date_debut ASC')):
            ateliers_eleve.append(at.date_debut)
            ateliers_eleve.append(at.date_fin)
            ateliers_eleve.append(at.jour_AP)
            ateliers_eleve.append(at.cours)
            ateliers_eleve.append(at.inscriptions_cour)

        # On enregistre les cours et les inscriptions à coté pour pouvoir travaillé dessus plus facilement
        # Dans la liste ateliers_eleve, les cours commencent à l'indice 3 et vont de 5 en 5
        # Même chose pour les inscriptions mais qui commencent à l'indice 4
        for i in range(3, len(ateliers_eleve)-1, 5):
            cours_eleves.append(ateliers_eleve[i])

        for j in range(4, len(ateliers_eleve), 5):
            inscriptions.append(ateliers_eleve[j])

        # On sépare les cours/inscriptions entre eux et on enlève le dernier ;
        for k in range(len(cours_eleves)):
            cours_eleves[k] = cours_eleves[k].split(";")
            inscriptions[k] = inscriptions[k].split(";")

        for l in range(len(cours_eleves)):
            cours_eleves[l].pop()
            inscriptions[l].pop()

        # Dictionnaire des indices selon le compteur qui permettra de retrouver les infos des cours selon ou est inscrits
        # Par exemple à la boucle n°0, il faut récupérer les élements dans la liste ayant pour indice 0,1,2,3
        # date de debut, date de fin, jour du cour, les infos du cour
        # (car pour chaque atelier, il y a 4 infos importantes ^^ et donc ensuite il faut passer aux 4 infos suivantes
        # il y a aussi une 5 ème info qui est les inscriptions et donc il faut passer par dessus elle car inutile)
        # Et donc pour passer aux élements suivants, dans la boucle suivante, dans le dico, le 1 vaudra 5 etc..
        # Ce qui permetra de parcourir tous les éléments : à la boucle 1, le code parcourera les élements ayant pour indice 5,6,7,8
        dico = {}
        depart = 0
        for m in range(len(ateliers_eleve)):
            dico[m] = depart
            depart += 5

        # On récupère les dates et les cours où est présent l'élève et on renvoie cela au site
        # Les inscriptions ressemblent à cela : [[5,8],[9,6],[20,59], etc ..]
        # La première liste correspond au premier cour, la deuxième au deuxième cour etc...
        # Et donc il faut récupérer le cour ou est présent l'élève selon chaque atelier
        compteur = -1
        for n in inscriptions:
            compteur += 1
            for element in n:
                if id in element:
                    # Si l'id de l'élève est présent, alors il est inscrit dans ce cour ci
                    # On récupère l'indice de la liste où est présent l'élève
                    # ateliers_eleve est une liste contenant les cours/inscriptions dans chacun une liste
                    # et ceux ci sont eux-mêmes des listes (c'est complexe mais ça marche)
                    # Exemple pour un atelier dans la liste ateliers_eleve
                    # : [18/03/2021,19/03/2021, Mardi, [[Math, Mr.reveret],[Histoire, Mme.Bidan]], [[7,9,8],[15,13,21]] etc...]
                    IN = inscriptions[compteur].index(element)
                    # On récupère le cour
                    cour = cours_eleves[compteur][IN]
                    # On récupère les dates et on le stock dans un autre liste
                    for o in range(dico[compteur], dico[compteur] + 3):
                        historiques_eleve.append(ateliers_eleve[o])
                    historiques_eleve.append(cour)

        # Pour pouvoir afficher les listes présentes sur le site, il faut les convertir du format str au format list
        # car pour chaque cour, la liste de celui-ci est au format str
        # Même principe que plus haut, on crée un dico pour pouvoir passer à chaque liste (qui contient le nom du cour avec le prof)
        # Et donc pour chaque tour de boucle, on se place sur la liste et on la convertie
        # Les dicos contiennent l'indice les listes de cours
        # Exemple: [18/03/2021, 19/03/2021, Mardi, [Math, Mr.reveret], 22/04/2021, etc..]
        dico2 = {}
        depart2 = 3
        for p in range(len(historiques_eleve)):
            dico2[p] = depart2
            depart2 += 4

        for q in range(int(len(historiques_eleve) / 4)):
            historiques_eleve[dico2[q]] = ast.literal_eval(
                str(historiques_eleve[dico2[q]]))

        return donnée_pageHistoriques("", "", historiques_eleve)


##################################################


# Fonction qui gère le cour de l'élève


@ app.route('/choix_jour_cour', methods=['POST'])
@ login_required
def choix_jour_cour():
    """
    Fonction qui permet aux élèves de secondes de choisir le jour où ils ont AP
    """
    id = request.form['id']
    jour_cour = request.form['jour_cour']

    if jour_cour == "Mardi":
        return cours_eleves(id, 2, "Mardi")
    else:
        return cours_eleves(id, 2, "Jeudi")


@ app.route('/choix_cour_eleve', methods=['POST'])
@ login_required
def choix_cour_eleve():
    """
    Fonction qui rentre dans la base de donnée le cour voulu par l'élève
    Fonction qui supprime le précédent cour sélectionné par l'élève s'il veut changer
    Si l'élève est hors délai ou le cour est déja complet, il est refusé
    """
    cour = request.form['cour_eleve']
    ajout_cour = cour.split(',')

    id_eleve = ajout_cour.pop(0)
    id_cour = ajout_cour.pop(0)

    # Liste qui sert à l'insertion du cour dans la bdd
    inscription = []
    inscription.append(id_eleve)
    inscription.append(id_cour)

    # Les listes et boucles qui suivent servent à récupérer les informations nécessaires à l'incription de l'élève
    # comme les dates d'inscriptions, l'effectif max du cour et le nombre de personnes déja inscrite
    dates = []
    personnes_deja_inscrite = []
    effectif_max = []
    atelier = []

    Session = sessionmaker(bind=engine)
    s = Session()

    for personne in s.query(Inscriptions).filter(text(f"cour={id_cour}")):
        personnes_deja_inscrite.append(personne.eleve)

    for nb in s.query(Cours).filter(text(f"id={id_cour}")):
        effectif_max.append(nb.effectif_max)
        atelier.append(nb.atelier)

    for dates_atelier in s.query(Ateliers).filter(text(f"id={atelier[0]}")):
        dates.append(dates_atelier.debut_inscription)
        dates.append(dates_atelier.fin_inscription)
    ###################################################

    # Sert à convertir les dates récupérer dans la base de donnée en format date
    # On ajoute un journée à la date de fin car on ne peut pas s'inscrire le jour même (à cause de l'heure)
    # (l'heure de la date de la fin est 0h00 et non 23h59)

    date_debut = datetime.strptime(dates.pop(0), '%d/%m/%Y')
    date_fin = datetime.strptime(dates.pop(0), '%d/%m/%Y') + timedelta(1)

    ###################################################
    date = datetime.today()

    # Vérifie si les dates d'inscriptions sont respectées et ainsi que l'effectif max du cour
    # Supprime la précédente inscription à un cour si l'élève veut changer
    if date_debut <= date and date <= date_fin and len(personnes_deja_inscrite) - 1 < effectif_max[0]:
        suppression("""
        DELETE FROM inscriptions
        WHERE eleve=?
        """, [id_eleve])
        insertion("""
        INSERT INTO inscriptions (eleve,cour)
        VALUES (?,?)
        """, inscription)
        return render_template('pageFinale.html')
    else:
        return render_template('pageEchec_inscriptions.html')
##################################################


if __name__ == "__main__":
    """
    Lance le serveur
    Threaded = True permet de mettre chaque requete sur un thread unique et non utilisé
    Car si toutes les requetes sont sur le même thread, si il y a beaucoup de monde,
    cela peut faire ralentir tout le monde voir faire cracher
    """
    app.run(debug=True, threaded=True)
