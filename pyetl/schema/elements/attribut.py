# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 09:28:45 2014

@author: 89965
"""
import copy
# schemas : description de la structure des objets

TYPES_A = {"T":"T", '':"T", "TEXTE":"T", "TEXT":"T", "ALPHA":"T", "NAME":"T",
           '"CHAR"':"T", "REGCLASS":"T",
           "E":"E", "ENTIER":"E", "INTEGER":"E", "INT":"E",
           "EL":"EL", "BIGINT":"EL", "LONG":'EL', "ENTIER_LONG":"EL",
           "D":"D", "DATE":"D", "TIMESTAMP":"D", "TIMESTAMP WITHOUT TIME ZONE":"D",
           "TIME WITHOUT TIME ZONE":"D",
           "TIMESTAMP WITH TIME ZONE":"Z",
           "F":"F", "FLOAT":'F', "REEL":"F", "REAL":"F", "FLOTTANT":"F", "DECIMAL":"N",
           "H":"H", "HSTORE":"H", "DATE AVEC ZONE":"Z",
           "DOUBLE PRECISION":"F", "NUMERIC":"N",
           "BOOLEEN":"B", "BOOLEAN":"B", "B":"B",
           "CASE A COCHER":"B", "CASE_A_COCHER":"B",
           "S":"S", "SEQUENCE":"S", "SEQ":"S", "SERIAL":"S",
           "BS":"BS", "SEQUENCE LONGUE":"BS", "BIGSERIAL":"BS",
           "I":"E", "SMALLINT":"E", "INTERVALLE":"I", "OID":"I"}
TYPES_S = {"T":"texte", "E":"entier", "EL":"entier_long", "D":"date", "H":"hstore", "B":"booleen",
           "F":"reel", 'Z':"date avec zone", "S":"sequence", 'BS':'sequence longue',
           "N":"numerique", 'A':'non defini'}




class Conformite(object):
    '''definition d'une conformite
    pour le moment seul les enums sont utilisees'''
    typeconv = {"E":int, "EL":int, "F":float, "T":str}
    def __init__(self, nom, typeval='', vmax=0, mode=1, modele=None):
        self.nom = nom
        self.nombase = nom
        if modele:
            self.force_alias = modele.force_alias
            self.type_conf = modele.type_conf
            self.type_val = modele.type_val
            self.min = modele.min
            self.max = modele.max
            self.max_strict = modele.max_strict
            self.min_strict = modele.min_strict
            self.ordre = modele.ordre.copy()
            self.stock = modele.stock.copy()
            self.ajust = modele.ajust.copy()
            self.valide = modele.valide.copy()
            self.defaut = modele.defaut
            self.vmax = modele.vmax
            self.version = modele.version
            self.mode = modele.mode
            self.utilise = modele.utilise
            self.usages = modele.usages[:]
            self.taille = modele.taille
            self.ajuste = modele.ajuste
            self.poids = modele.poids
            self.valide_base = modele.valide_base
        else:
            self.force_alias = 0
            self.type_conf = 0
            self.type_val = ''
            if typeval:
                self.type_val = TYPES_A[typeval.upper()]
            self.min = None
            self.max = None
            self.max_strict = False
            self.min_strict = False

            self.ordre = dict()
            self.stock = dict()
            self.ajust = dict()
            self.valide = set()
            self.defaut = ''
            self.vmax = vmax
            self.version = 0
            self.mode = mode
            self.utilise = False
            self.usages = []
            self.taille = 0
            self.dec = 0
            self.ajuste = False
            self.poids = 0
            self.valide_base = False

    def stocke_valeur(self, valeur, alias, mode_force=1, ordre=0):
        '''range une valeur de conformite avec gestion des alias'''
#        print ("schema stocke valeur ", self.nom, valeur,alias,mode_force)
        valeur = str(valeur)
        alias = str(alias)


        if valeur == alias: # les 2 sont identiques le forcage n'a pas de sens
            mode_force = 0
#            raise

        if ordre == 0:
            ordre = len(self.stock)

        self.force_alias = max(mode_force, self.force_alias)
        if alias == "##defaut##":
            self.ajust[""] = valeur

        if mode_force == 0:
            self.ajust[valeur] = valeur
            self.valide.add(valeur)
        elif mode_force == 1:
            try:
                int(valeur)
                self.ajust[valeur] = alias
                self.valide.add(alias)
            except ValueError:
                self.ajust[valeur] = valeur
                self.valide.add(valeur)
        elif mode_force == 2:
            self.ajust[valeur] = alias
            self.valide.add(alias)
#            print( '----------------------------------detecte mode 2 ', valeur, alias, self.valide,self.ajust)

        elif mode_force == 3:
            self.ajust[alias] = valeur
            self.valide.add(valeur)

        self.stock[valeur] = (valeur, alias, ordre, mode_force, self.ajust[valeur])


    def copie(self):
        '''retourne une copie sans les valeurs stockeees'''
        cop2 = Conformite(self.nom[:], modele=self)
        return cop2




    def ajuste_valeur(self, val):
        '''cre un mecanisme d'alias permettant d'ajuster les donnees en entree'''
        self.ajuste = True # on a ajuste des valeurs sur ce schema

        try:
            return self.ajust[val]
        except KeyError:
#            if val: print ('clef non trouvee:', val,self.ajust)
            return val

    def valide_valeur(self, val):
        '''verifie si un attribut est conforme'''
        return val in self.valide

    def calcule_longueur(self):
        '''taille maxi de chaine de la liste de conformites'''
#        --self.taille = max([len(i) for i in self.valeurs])
        self.taille = max(map(len, self.stock.keys()))

    def stocke_min(self, valeur, strict):
        '''mini d'un intervalle'''
        self.min = valeur
        self.min_strict = strict
        self.type_conf = 3 if self.min and self.max \
                                and not (self.max_strict or self.min_strict) else 2

    def stocke_max(self, valeur, strict):
        '''maxi d'un intervalle'''
        self.max = valeur
        self.max_strict = strict
        self.type_conf = 3 if self.min and self.max \
                                and not (self.max_strict or self.min_strict) else 2

    def __repr__(self):
        return str([self.stock[i][0] for i in self.stock])


class Attribut(object):
    ''' gestion des attributs'''
    types = {type(1):"entier",
             type(1.1):"flottant", type("a"):"texte"}
    types_a = TYPES_A
    types_s = TYPES_S

    def __init__(self, nom, vmax, nom_conformite=''):
        self.nom = nom
        self.valeurs = dict()
        self.conf = True if vmax else False
        self.vmax = vmax

        self.type_att = "A"
        self.type_att_base = "A"
        self.multiple = False
        self.graphique = False
        self.conformite = None
        self.nom_conformite = nom_conformite
        self.defaut = None
        self.version = 0
        self.alias = ''
        self.oblig = False
        self.taille = 0
        self.dec = 0
        self.ordre = 0
        self.nom_court = ''
        self.nom_sortie = ''
        self.unique = False
        self.def_index = ''
        self.clef_etr = ''


    def set_type(self, val):
        """positionne le type de l attribut"""
        if self.type_att == 'T':
            return # on est deja en mode texte c'est pas la peine de continuer
        if self.type_att < 'F':
            try:
                v_test = int(val)
                if abs(v_test) > 1000000000:
                    self.type_att = "EL"
                else:
                    self.type_att = "E"
                return # on reste en mode entier
            except ValueError:
                self.type_att = "F"
        try:
            v_test = float(val)
        except ValueError:
            self.type_att = "T"
        return

    def setbasic(self, mode):
        ''' retourne une structure basique'''
        if not mode:
            return
        self.nom_conformite = ''
        self.defaut = None
        if mode == 'basic':
            self.conformite = None
            self.type_att = self.type_att_base


    def copie(self, nom=None):
        ''' retourne un clone de l'attribut '''
        conf = self.conformite
        self.conformite = ''
        nouveau = copy.deepcopy(self)
        nouveau.conformite = conf
        self.conformite = conf
        if nom is not None:
            nouveau.nom = nom
        return nouveau

    def __deepcopy__(self, memo):
        '''evite les copies des conformites'''
#        conf = self.conformite
#        self.conformite = ''
        nouveau = copy.copy(self)
        self.valeurs = self.valeurs.copy()
#        nouveau.conformite = conf
#        self.conformite = conf
        return nouveau





    def ajout_valeur(self, valeur):
        ''' analyse d'une valeur pour la determination automatique des conformites'''
        if valeur is None:
            return
        val = str(valeur)
        if self.conf:
            self.valeurs[val] = self.valeurs.get(val, 0)+1
            self.conf = len(self.valeurs) <= self.vmax
        if val:
            self.set_type(val)
#            print('ajout_valeur', type(self.taille), self.taille)
            self.taille = max(self.taille, len(val))
            if self.type_att == 'F':
                if "." in val:
                    liste_parties = val.split('.')
                    self.dec = max(self.dec, len(liste_parties[1]))


    def get_type(self):
        '''recupere le type d'un attribut'''
#        print ('si:type_attribut',self.type_att,TYPES_S.get(self.type_att))
        return TYPES_S.get(self.type_att, TYPES_S.get(self.type_att_base, self.type_att))

    def __repr__(self):
        return str((self.nom, self.type_att, self.nom_conformite))
