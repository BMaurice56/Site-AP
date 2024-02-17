from sqlalchemy import create_engine, Column, String, Integer, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

engine = create_engine('sqlite:///database/base_de_donnée_AP.db', echo=True)
Base = declarative_base()

########################################################################


class Utilisateur(Base):
    __tablename__ = "personnes"

    id = Column(Integer, primary_key=True)
    nom = Column(String)
    prenom = Column(String)
    classe = Column(String)
    niveau = Column(Integer)
    identifiant = Column(String)
    mdp = Column(String)
    statut = Column(String)

    def __init__(self, id, nom, prenom, classe, niveau, identifiant, mdp, statut):
        self.id = id
        self.nom = nom
        self.prenom = prenom
        self.classe = classe
        self.niveau = niveau
        self.identifiant = identifiant
        self.mdp = mdp
        self.statut = statut


class Inscriptions(Base):
    __tablename__ = "inscriptions"

    eleve = Column(Integer, primary_key=True)
    cour = Column(Integer)

    def __init__(self, eleve, cour):
        self.eleve = eleve
        self.cour = cour


class Ateliers(Base):
    __tablename__ = "ateliers"

    id = Column(Integer, primary_key=True)
    niveau = Column(Integer)
    date_debut = Column(String)
    date_fin = Column(String)
    debut_inscription = Column(String)
    fin_inscription = Column(String)
    jour_AP = Column(String)

    def __init__(self, id, niveau, date_debut, date_fin, debut_inscription, fin_inscription, jour_AP):
        self.id = id
        self.niveau = niveau
        self.date_debut = date_debut
        self.date_fin = date_fin
        self.debut_inscription = debut_inscription
        self.fin_inscription = fin_inscription
        self.jour_AP = jour_AP


class Cours(Base):
    __tablename__ = "cours"

    id = Column(Integer, primary_key=True)
    atelier = Column(Integer)
    nom = Column(String)
    professeur = Column(Integer)
    effectif_max = Column(Integer)

    def __init__(self, id, atelier, nom, professeur, effectif_max):
        self.id = id
        self.atelier = atelier
        self.nom = nom
        self.professeur = professeur
        self.effectif_max = effectif_max


class Professeurs(Base):
    __tablename__ = "professeurs"

    id = Column(Integer, primary_key=True)
    nom = Column(String)

    def __init__(self, id, nom):
        self.id = id
        self.nom = nom


class Historiques(Base):
    __tablename__ = "historiques"

    id = Column(Integer, primary_key=True)
    niveau = Column(Integer)
    date_debut = Column(String)
    date_fin = Column(String)
    debut_inscription = Column(String)
    fin_inscription = Column(String)
    jour_AP = Column(String)
    cours = Column(String)
    inscriptions_cour = Column(String)

    def __init__(self, id, niveau, date_debut, date_fin, debut_inscription, fin_inscription, jour_AP, cours, inscriptions_cour):
        self.id = id
        self.niveau = niveau
        self.date_debut = date_debut
        self.date_fin = date_fin
        self.debut_inscription = debut_inscription
        self.fin_inscription = fin_inscription
        self.jour_AP = jour_AP
        self.cours = cours
        self.inscriptions_cour = inscriptions_cour


# create tables
Base.metadata.create_all(engine)
