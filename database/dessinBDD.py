import sqlite3
from random import randint

# création de la base DB
connexion = sqlite3.connect("base_de_donnée_AP.db")
# création du curseur
curseur = connexion.cursor()

# création de la table personnes
curseur.execute("DROP TABLE IF EXISTS personnes")
curseur.execute("""
CREATE TABLE personnes 
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nom TEXT,
prenom TEXT,
classe TEXT,
niveau INT,
identifiant TEXT,
mdp TEXT,
statut TEXT
)
""")

connexion.commit()


# création de la table ateliers
curseur.execute("DROP TABLE IF EXISTS ateliers")
curseur.execute("""
CREATE TABLE ateliers 
(
id INTEGER PRIMARY KEY AUTOINCREMENT,
niveau INT,
date_debut TEXT,
date_fin TEXT,
debut_inscription TEXT,
fin_inscription TEXT,
jour_AP TEXT
)
""")

connexion.commit()


# création de la table cours
curseur.execute("DROP TABLE IF EXISTS cours")
curseur.execute("""
CREATE TABLE cours (
id INTEGER PRIMARY KEY AUTOINCREMENT, 
atelier INT,
nom TEXT,
professeur INT,
effectif_max INT
)
""")


connexion.commit()


# création de la table professeurs
curseur.execute("DROP TABLE IF EXISTS professeurs")
curseur.execute("""
CREATE TABLE professeurs (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nom TEXT
)
""")


connexion.commit()


# création de la table inscriptions
curseur.execute("DROP TABLE IF EXISTS inscriptions")
curseur.execute("""
CREATE TABLE inscriptions (
eleve INT,
cour INT,
PRIMARY KEY (eleve))
""")

connexion.commit()

curseur.execute("INSERT INTO personnes (nom,prenom,classe,niveau,identifiant,mdp,statut) VALUES ('Maurice', 'Benoit', 'T5', 0, 'bmaurice', '86d2b56b964f0104f92b17e664604ee138ede5ea7880c58c3ffbcfabef940710', 'Elève')")
curseur.execute("INSERT INTO personnes (nom,prenom,classe,niveau,identifiant,mdp,statut) VALUES ('Perrot', 'Jean', 'T2', 0, 'jperrot','86d2b56b964f0104f92b17e664604ee138ede5ea7880c58c3ffbcfabef940710', 'Elève')")
curseur.execute("INSERT INTO personnes (nom,prenom,classe,niveau,identifiant,mdp,statut) VALUES ('Bonaly', 'David', 'T4', 0, 'dbonaly','86d2b56b964f0104f92b17e664604ee138ede5ea7880c58c3ffbcfabef940710', 'Elève')")
curseur.execute("INSERT INTO personnes (nom,prenom,classe,niveau,identifiant,mdp,statut) VALUES ('Fourrier', 'Baudouin', 'T3', 0, 'bfourrier','86d2b56b964f0104f92b17e664604ee138ede5ea7880c58c3ffbcfabef940710', 'Elève')")
curseur.execute("INSERT INTO personnes (nom,prenom,classe,niveau,identifiant,mdp,statut) VALUES ('Ménahèze', 'Ewan', 'T6', 0, 'emenaheze','86d2b56b964f0104f92b17e664604ee138ede5ea7880c58c3ffbcfabef940710', 'Elève')")
curseur.execute("INSERT INTO personnes (nom,prenom,classe,niveau,identifiant,mdp,statut) VALUES ('Chaize', 'Marin', 'T5', 0,'mchaize','86d2b56b964f0104f92b17e664604ee138ede5ea7880c58c3ffbcfabef940710', 'Elève')")
curseur.execute("INSERT INTO personnes (nom,prenom,classe,niveau,identifiant,mdp,statut) VALUES ('Lecourtois', 'Clément', 'T7', 0, 'clecourtois', '86d2b56b964f0104f92b17e664604ee138ede5ea7880c58c3ffbcfabef940710', 'Elève')")
curseur.execute("INSERT INTO personnes (nom,prenom,identifiant,mdp,statut) VALUES ('admin', 'admin','admin', '626270df6622df4b6c744e59a6d20ac16bf8e4cdc16a58e379dc95a77ce4a996', 'Administrateur')")


for i in range(1, 11):
    classe = randint(1, 7)
    curseur.execute(
        f"INSERT INTO personnes (nom,prenom,classe,niveau,identifiant,mdp,statut) VALUES ('toto','toto{i}','P{classe}',1,'toto{i}','913b891f804f3e345569f05b7c26aad33f78e791c33968c3015f862258617269','Elève')")

for i in range(1, 11):
    classe = randint(1, 7)
    curseur.execute(
        f"INSERT INTO personnes (nom,prenom,classe,niveau,identifiant,mdp,statut) VALUES ('touriste','touriste{i}','S{classe}',2,'touriste{i}','907c609179ce22bd83e2c27449efeb9e03180ef3d4a2ef9ab5b5283168fc82e9','Elève')")


connexion.commit()
