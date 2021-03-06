# -*- coding: utf-8 -*-
"""
Created on Fri Oct 21 13:20:44 2016

@author: 89965
vrapper virtuel permettant d'acceder a des bases monofichier
type access, sqlite... en envoyant un objet virtuel a un lecteur de base de donnees

"""
import os
from .interne.objet import Objet
from .db import DATABASES
#types de bases fichier connues

def lire_objets(rep, chemin, fichier, stock_param, regle):
    """ prepare l objet virtuel declencheur pour la lecture en base access ou sqlite"""
#    type_base = {".mdb":"access",
#                 ".sqlite":"sqlite"}
    type_base = {DATABASES[i].fileext:i for i in DATABASES if DATABASES[i].svtyp == 'file'}
    traite_objet = stock_param.moteur.traite_objet
#    regle = stock_param.regles[0]
    ext = os.path.splitext(fichier)[1]
    base = os.path.splitext(fichier)[0]
#    stock_param.parms["serveur_"+base]=chemin
    obj = Objet('__filedb', base, format_natif='interne')
    obj.attributs["#racine"] = rep
    obj.attributs["#chemin"] = chemin
    obj.attributs["#nombase"] = fichier
    obj.attributs["#base"] = os.path.join(rep, chemin, fichier)
    force = stock_param.get_param('F_entree')
    type_base_demande = '.'+force if force else ext
    type_base_trouve = type_base.get(type_base_demande)
    if type_base_trouve:
        obj.attributs["#type_base"] = type_base_trouve
#        obj.debug("filedb:virtuel")
        obj.virtuel = True
#        print ('traitement filedb: ', obj.attributs["base"])
        traite_objet(obj, regle)
        return 1
    print('error: fildb: type_base inconnu', type_base_demande)
    return 0
