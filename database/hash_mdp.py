import sqlite3
import hashlib

# création de la base DB
connexion = sqlite3.connect("base_de_donnée_AP.db")
# création du curseur
curseur = connexion.cursor()

mdp = hashlib.sha256()
mdp.update("Elève".encode())

print(mdp.hexdigest())

