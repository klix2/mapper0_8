# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 09:28:45 2014

@author: 89965
"""
#import copy
import re
from . import attribut as A
from . import mapping as MP
# schemas : description de la structure des objets
TYPES_G = {'0':"NOGEOM", '1':"POINT", '2':"LIGNE", '3':"SURFACE",
           '-1':"GEOMETRIE", '4':"TIN", '5':"POLYHEDRAL", 'indef':"NOGEOM"}
CODES_G = {"NOGEOM":'0', 'ALPHA':'0', "":'0',
           "POINT":'1',
           "LIGNE":'2', 'MULTILINESTRING':'2', 'MULTICURVE':'2',
           "CONTOUR":'3', "SURFACE":'3', "MULTISURFACE":'3', 'MULTIPOLYGON':'3', 'POLYGONE':'3',
           "TIN":'4',
           "POLYHEDRALSURFACE":'5',
           "GEOMETRIE":'-1', "GEOMETRY":'-1'}
HIERARCHIE = {'P':1, 'U':2, 'K':3, 'X':4, 'I':4}

def _gestion_types_simples(attr, type_attribut):
    ''' decode les types classiques'''
    type_attr = type_attribut.upper()
#            print ('type_attribut',type_attr)
    taille = 0
    dec = 0
    if '[]' in type_attr:
        type_attr = type_attr.replace('[]', '')
        attr.multiple = True
    if '(' in type_attr:
        dtyp = type_attr.split('(')
        type_attr = dtyp[0]
        complements = dtyp[1].replace(')', '')
        cmp = complements.split(',')
        if len(cmp) == 1:
            taille = int(cmp[0])
        if len(cmp) == 2:
            dec = int(cmp[1])
    if type_attr in A.TYPES_A:
        attr.type_att = A.TYPES_A[type_attr]
    elif type_attr[0] == 'T' and type_attr[1:].isdigit():
        attr.type_att = "T"
        attr.taille = int(type_attr[1:])
    elif type_attr[0] == 'E' and type_attr[1:].isdigit():
        attr.type_att = 'E'
        attr.type_att_base = "E"
        attr.taille = int(type_attr[1:])
        attr.dec = 0
    elif type_attr[0] == 'E' and type_attr[1:-1].isdigit() and type_attr[-1] == 'S':
        attr.type_att = 'E'
        attr.type_att_base = "E"
        attr.taille = int(type_attr[1:-1])
        attr.dec = 0
    elif type_attr[0] == 'E' and re.match('E[0-9]+_[0-9]+', type_attr):
        attr.type_att = 'E'
        attr.type_att_base = "E"
        attr.taille = len(type_attr.split('_')[1])
    elif type_attr == 'X': # attribut non traite
        attr.type_att = "X"
        attr.type_att_base = "X"
    elif type_attr == 'A': # attribut non traite
        attr.type_att = "A"
        attr.type_att_base = "A"
    elif type_attr == 'N': # attribut non traite
        attr.type_att = "N"
        attr.type_att_base = "N"
    else:
#                print("schema: type attribut inconnu ", self.groupe, self.nom,
#                      " : texte par defaut ",
#                      attr.nom+'->'+type_attribut, type_attribut in CODES_G)
        print('schemaclasse--------attention type inconnu passage en texte--->', attr, type_attr)
        attr.type_att = "T"
    if attr.type_att_base == "E" and attr.taille > 6:
        attr.type_att_base = "EL"
        attr.taille = taille
        attr.dec = dec






class SchemaClasse(object):
    ''' description de la structure d'un objet'''
    types_stock = {'r':'table', 'v':'vue', 'm':'vue materialisee', 's':'table systeme',
                   'f':'table distante', 'c':'couche', 'i':'interne', 'd':'fichier'}

    def __init__(self, ident, schema, debug=0):
        groupe, nom = ident
        self.info = {"nom_geometrie":"geometrie", "dimension":"2",
                     "type_geom":"indef", "objcnt_init":'0', "courbe":""}
        self.ident_origine = ident
        self.nom = nom
        self.autodim = False
        self.alias = ''
        self.groupe = groupe
        self.nbr = 0 # nbre d'objets analyses
        self.srid = 3948
        self.sridmixte = False
#        self.nom_geometrie = 'geometrie'
        self.multigeom = False
#        self.courbe = False
        self.changed = False
#        self.dimension = 2
        self.force_dim = False
        self.ajust_enums = dict() # le schema comprend des conformites ajustables
        self.confs = dict() # le schema comprend des conformites verifiables
        self.v_3d = 0
        self.ordrealpha = False # on range par order alpha
        self.liste_attributs_cache = [] # liste ordonnee d'attributs
        self.fichier = ""
        self.utilise = False
        self.attributs = dict()
        self.attmap = dict()
        self.regles_modif = set() # liste des regles qui ont modifie la classe
        self.objcnt = 0
        self.verrouille = False
        self.conversion_noms = False
#        self.version = 0
        self.schema = schema # schema d'appartenance
        self.errpr = ''
        self.errcnt = 0
        self.npr = 0
        self.ech_denom_max = 0
        self.ech_denom_min = 0
        self.fils = []
        self._pkey = set() # pour les tests d'unicite de clef primaire
        self.triggers = dict()
        self.indexes = dict()
        self.debug = debug
        self.minmaj = ''
        self.minmajfunc = lambda x: x
        self.type_table = 'i' # table par defaut
        self.poids = 0
        self.stable = True
        self.a_sortir = True # determine si une classe doit etre ecrite
        self.specifique = dict() # elements specifiques a certains formats
        self.adapte = False
        self.use_noms_courts = False
        self.noms_courts = set()
        self.cibles = set()
        self.basic = False

    def setbasic(self, mode):
        '''simplifie la striucture pour les classes de consultation '''
        self.triggers = dict()
        self.specifique = dict()
        self.changed = True
        self.type_table = 'i'
        self.basic = mode
        for i in self.attributs.values():
            i.setbasic(mode)


    @property
    def identclasse(self):
        '''retourne l'identifiant de classe : groupe,nom'''
        return (self.groupe, self.nom)

    def setident(self, ident):
        '''repositionne l identifiant'''
        self.groupe, self.nom = ident

    @property
    def dbident(self):
        '''retourne l'identifiant de classe sous forme 'groupe'.'nom' pour acces base de donnees '''
        return "'"+self.groupe+"'.'"+self.nom+"'"

    @property
    def nomschema(self):
        ''' retourne le nom du schema auquel appartient la classe'''
        return self.schema.nom if self.schema else ''

    @property
    def getpkey(self):
        ''' retourne la liste de champs comportant la clef principale'''

#        pk = ','.join([self.minmajfunc(str(self.indexes[i]))
#                         for i in sorted(self.indexes) if i[0] == 'P'])
#        if pk=='i':
#            print ( 'indexes:',self.indexes)
#            raise
        return ','.join([self.minmajfunc(str(self.indexes[i]))
                         for i in sorted(self.indexes) if i[0] == 'P'])

    @property
    def haspkey(self):
        """vrai si la classe a une clef primaire"""
        return 'P:1' in self.indexes

    @property
    def pkey_simple(self):
        ''' vrai si la clef principale comprend un seul champ'''
        return len([i for i in sorted(self.indexes) if i[0] == 'P']) == 1

    @property
    def fkeys(self):
        '''genere le dictionnaire des clefs_etrangeres
            fkey stocke sous forme d'un dictionnaire attribut:groupe.classe.attribut'''
        if self.basic == 'basic':
            return dict()
        return {i:j.clef_etr for i, j in self.attributs.items() if j.clef_etr}

    def getinfo(self, nom, defaut=''):
        '''recupere une info du schema'''
        return self.info.get(nom, defaut)

    def setinfo(self, nom, valeur):
        '''recupere une info du schema'''
        self.info[nom] = valeur


    def dicindexes(self):
        ''' genere le dictionnaire des indexes de la classe '''

        defindexes = dict()
        nbkeys = 0
        for i in self.fkeys:
            nbkeys += 1
            defindexes['K'+str(nbkeys)] = [i]
#        print ('defindexes:',self.nom,self.indexes)
        for i in sorted(self.indexes.keys()):
            nom = i.split(':')[0]
            if nom in defindexes:
                defindexes[nom].append(self.indexes[i])
            else:
                defindexes[nom] = [self.indexes[i]]
        valid = dict()
        for i in defindexes:
            champs = ','.join(defindexes[i])
            nature = i[0]
            if champs not in valid or HIERARCHIE[valid[champs][0]] > HIERARCHIE[nature]:
                valid[champs] = i

        return {valid[i]:i for i in valid}

    @property
    def listindexes(self):
        ''' genere une representation lisible des autres indexes '''
        defindexes = self.dicindexes()
#        print ('dicindexes:',defindexes,self.indexes)
#        print (' '.join([nom+':'+self.minmajfunc(defindexes[nom])
#                for nom in sorted(defindexes.keys())]))
        return ' '.join([nom+':'+self.minmajfunc(defindexes[nom])
                         for nom in sorted(defindexes.keys())])
#        return ' '.join([nom+':'+','.join([self.minmajfunc(k) for k in defindexes[nom].split(',')])
#                         for nom in sorted(defindexes.keys())])

    def index_par_attributs(self):
        ''' genere un recapitulatif des indexes par attribut'''
        defindexes = self.indexes
        dicatt = dict()
#        print ('defindexes:',self.nom,self.indexes)
        for i in defindexes:
            if defindexes[i] in dicatt:
                dicatt[defindexes[i]] += ' '+i
            else:
                dicatt[defindexes[i]] = i

#        for i in sorted(defindexes.keys()):
#            for nom in defindexes[i]:
#                if nom in dicatt:
#                    dicatt[nom].append(i)
#                else:
#                    dicatt[nom]=[i]
        return dicatt

    def setdim(self, dim):
        """positionne la dimension geometrique"""
#        self.is_3d = True if dim == 3 or dim =='3' else False
        self.info["dimension"] = dim
        self.changed = True
        self.type_table = 'i'

    def setsortie(self, f_sortie, rep_sortie=None):
        """positionne le format du schema pour l ecriture"""
        self.schema.format_sortie = f_sortie.nom_format
        if rep_sortie is not None:
            self.schema.rep_sortie = rep_sortie
#        print('setsortie:dialecte sql:',f_sortie.dialecte)
        if f_sortie.dialecte and f_sortie.dialecte != 'natif':
            self.schema.dbsql = f_sortie.writerparms['dialecte'].gensql()
        elif self.schema.dbsql:
            f_sortie.writerparms['dialecte'] = f_sortie.databases[self.schema.dbsql.dialecte]


    def amodifier(self, regle, dyn=False):
        ''' determine si une modif de schema a deja ete faite
        ( on garde en memoire le numero de regle)'''
        idregle = regle.numero
#        print ('amodifier',idregle,self.regles_modif,idregle in self.regles_modif)
        if dyn:
            return True
        if idregle in self.regles_modif:
            return False
        self.regles_modif.add(idregle)
        return True


    def setorig(self, idorig):
        '''positionne l'origine de la classe
        cet identifiant permet de creer le fichier de mapping'''
        self.ident_origine = idorig

    def setpkey(self, liste):
        '''cree stocke la definition des champs de la clef primaire'''
#        print ("setpkey",self.indexes,liste)
        for i in list(self.indexes.keys()):
            if i.startswith("P:"):
                del self.indexes[i]
        if liste:
            self.indexes.update({('P:'+str(i+1), j)for i, j in enumerate(liste) if j})


# gestion des clefs etrangeres
    def listfkeys(self):
        '''genere une representation lisible des clefs etrangeres'''
        return (','.join([self.minmajfunc(i)+'->'+self.minmajfunc(self.fkeys[i])
                          for i in sorted(self.fkeys.keys())]))

    def setfkey(self, attribut, cible):
        ''' ajoute une clef etrangere a la classe '''
        self.attributs[attribut].clef_etr = cible
        self.type_table = 'i'

    def getfkey(self, attribut):
        ''' ajoute une clef etrangere a la classe '''
        return self.attributs[attribut].clef_etr

    def renomme_cible_classe(self, id_classe, nouv_classe):
        """renomme les cibles de clef etrangeres"""
        niv1, cla1 = id_classe
        niv2, cla2 = nouv_classe
        for attr, cible in list(self.fkeys.items()):
            niveau, classe, attribut = cible.split('.')
            if cla1:
                if niv1 == niveau and cla1 == classe:
                    cible2 = '.'.join((niv2, cla2, attribut))
                    self.attributs[attr].clef_etr = cible2
            else:
                if niv1 == niveau:
                    cible2 = '.'.join((niv2, classe, attribut))
                    self.attributs[attr].clef_etr = cible2

    def addindex(self, index):
        ''' ajoute des definitions d'indexes'''
        self.indexes.update(index)
        self.changed = True
        self.type_table = 'i'

    def setminmaj(self, valeur):
        ''' cree les fonctions de coversio min mahj pour les formats'''
        if self.minmaj == valeur:
            return
        self.minmaj = valeur
        if self.minmaj == 'up':
            self.minmajfunc = str.upper
        elif self.minmaj == 'low':
            self.minmajfunc = str.lower
        else:
            self.minmajfunc = str




    @property
    def fkey_dep(self):
        '''genere la liste des dependances externes pour la classe'''
        deps = set()
        for i in self.fkeys:
            niveau, classe, _ = self.fkeys[i].split('.')
            deps.add((niveau, classe))
        return deps

    @property
    def fkey_attribs(self):
        '''genere la liste des attributs ayant de dependances externes pour la classe'''
        return set(self.fkeys.keys())

    def supprime_attribut(self, nom):
        '''enleve un attribut du schema'''
        self.type_table = "i"

        if nom in self.attributs:
            del self.attributs[nom]
            self.liste_attributs_cache = []

    def rename_attribut(self, nom, nouveau_nom, modele=None):
        """renomme un attribut en gerant les indexes et les clefs """
        self.type_table = "i"
        self.changed = True

        if nouveau_nom in self.attributs:
#                print ('renommage inutile attribut ',self.identclasse,':', nom ,'->', nouveau_nom)

            return
        if nom in self.attributs:
#                print ('renommage attribut ',self.identclasse,':', nom ,'->', nouveau_nom)
            self.attributs[nouveau_nom] = self.attributs.pop(nom)
            self.attributs[nouveau_nom].nom = nouveau_nom
            if nom in self.indexes.values():
                for i in self.indexes:
                    if self.indexes[i] == nom:
                        self.indexes[i] = nouveau_nom
        else:
#            print('renommage attribut creation', self.identclasse, ':',
#                  nouveau_nom)
            self.ajout_attribut_modele(modele, nom=nouveau_nom)

#        print ('renommage attribut ',self.identclasse,':', nom ,'->', nouveau_nom, self.getpkey)

        self.liste_attributs_cache = []



    def garder_attributs(self, liste, ordre=False):
        ''' ne conserve que les attributs de la liste, au besoin les cree...'''
        att = dict()
        self.type_table = "i"

        for num, i in enumerate(liste):
            if i in self.attributs:
                att[i] = self.attributs[i]
            else:
                att[i] = A.Attribut(i, 0)
            if ordre:
                att[i].ordre = num
        self.attributs = att
        self.liste_attributs_cache = []

#        print ('dans schema_garder_attributs',liste, self.attributs.keys())


    def ajuste_valeurs(self, obj): # cas particuliers de mappings en entree
        ''' remplace des valeurs d 'enum en entree a la volee'''
        for i in self.ajust_enums:
            valeur = obj.attributs[i]
            if valeur in self.ajust_enums[i]:
#                print ('shp:ajustement',i,obj.attributs[i],'->',self.ajust_enums[i][v])
                obj.attributs[i] = self.ajust_enums[i][valeur]

    def controle_pk(self, pkey, err):
        ''' valide l'unicite de la clef primaire'''
        if pkey in self._pkey:
            err.append('clef duppliquee :'+ pkey)
        else:
            self._pkey.add(pkey)

    def controle_conformites(self, obj, err):
        ''' valide les conformites à la lecture'''
    #    print ('conformites a controler',confs)

        for i in self.confs.items():
            nom, vals = i
            if obj.attributs[nom] not in vals:
                err.append('erreur conformite ' + nom +':->'+obj.attributs[nom]+'<-')


    def adapte_attributs(self, fonction):
        ''' renommage en bloc des attributs avec une fonction
        qui retourne les noms modifies par ex tout passer en minuscule'''
        self.changed = True
        self.type_table = 'i'
        for i in list(self.attributs.keys()):
            self.rename_attribut(i, fonction(i))
        self.liste_attributs_cache = []

    def remap_attribut(self, nom, mapnom):
        ''' positionne les mappings d'entree et de sortie '''
        self.changed = True
        self.type_table = 'i'
        if nom in self.attributs:
            attr = self.attributs[nom]
            if attr.nom_court:
                del self.attmap[attr.nom_court]
            attr.nom_court = mapnom
            if mapnom:
                self.attmap[mapnom] = attr
        self.liste_attributs_cache = []


    def init_mapping(self, schema_destination, qual):
        ''' recherche une correspondance pour la classe'''
        MP.match_classe(self, schema_destination, qual)





    def adapte_schema_classe(self, liste_attributs):
        '''adapte les schemas de destination pour pas faire des incoherences
        (supprime les attributs obligatoites non existant dans la source)'''
        self.adapte = True
        self.type_table = "i"
        self.changed = True

        liste_att = set(liste_attributs)
#        print ('attributs',la,list(self.attributs.keys()))
        for i in list(self.attributs.keys()):
            if i not in liste_att: # on essaye de creer un attribut on regarde si on a le droit

                att = self.attributs[i]
#                print('---------attributs a supprimer ', i, att.nom, att.oblig)

                if att.oblig: #on peut pas creer un obligatoire sautf si defaut (pas encore géré)
                    if not att.defaut:
                        continue
                    if att.type_att == "S" or att.type_att == "BS":
                        continue
                    del self.attributs[i]
                    print('SC: adapte_schema: attribut obligatoire inexistant supprime', i)
        self.liste_attributs_cache = []




    def _gestion_clef_etr(self, attr, clef_etr):
        ''' gere les definitions de clef etrangeres sur les attributs '''
        if not clef_etr:
            return
        if self.debug:
            print('schema : detection clef >', clef_etr, '<')
        nom = attr.nom
        attr.clef_etr = clef_etr
        # on verifie qu'il y a un index
        match = 0
        for ind in self.listindexes.split(' '): # on verifie qu'un index ordinaire matche
#            print ('clef_pk',ind,self.listindexes)
            if ind and ind.split(':')[1] == nom:
                match = 1
        if not match and not attr.unique: # il n'u a pas d'index (unique implique un index)
            nmax = 0
            for i in self.indexes:
                if 'X' in i:
                    nmax = max(nmax, int(i[1]))

            nom_index = 'X'+str(nmax+1)+':1'
#            print ('index :',(nom_index,attr.nom))
            self.addindex(((nom_index, attr.nom),))

#        print('schema : detection clef >'+clef+'<',index_ordinaire)






    def _gestion_index(self, attr, index):
        '''gere les definitions d'index'''
        if not index:
            return
        if index.startswith("FK:"):
            clef = index[3:]
            self._gestion_clef_etr(attr, clef)
            attr.oblig = True
        elif index == 'P' or index == 'PK':
            self.addindex({'P:1':attr.nom})
            attr.oblig = True
        else:
            self.addindex({i:attr.nom for i in index.upper().split(' ')})


    def _gestion_enums(self, attr, type_attribut):
        '''gere un attribut de type enum'''
        attr.nom_conformite = type_attribut
        attr.conformite = self.schema.conformites[type_attribut]
        attr.conformite.utilise = True
        if attr.conformite.force_alias: # attention possibilites de forcage
#                print ("schema: definition d'un forcage",self.nom,attr.nom)
            self.ajust_enums[attr.nom] = attr.conformite.ajust
        self.confs[attr.nom] = attr.conformite.valide # controles de conformite
        if not attr.oblig:
            self.confs[attr.nom].add('')
        attr.taille = attr.conformite.taille
        attr.type_att_base = "T"
        attr.type_att = "T"






    def _gestion_type_attribut(self, attr, type_attribut=None, defaut=None):
        '''stocke le type d'un attribut et les valeurs par defaut'''
#        print ('type_init',type_attribut)

        type_attribut = type_attribut if type_attribut is not None else attr.type_att
        defaut = defaut if defaut is not None else attr.defaut
        if not type_attribut:
            return
        if self.schema and type_attribut in self.schema.conformites:
#            print ('gestion enums',type_attribut)
            self._gestion_enums(attr, type_attribut)
        else:
            _gestion_types_simples(attr, type_attribut)
        if defaut:
            #print 'valeurs defaut',nom,defaut
            attr.defaut = defaut
            if defaut[0] != 'V':
                attr.conf = False
            # evite les conformites sur les sequences et autres attributs calcules

    def _gestion_ordre_insertion(self, attr, ordre, mode_ordre='r'):
        ''' gere la position d'insertion d'un attribut '''

        if mode_ordre == 'r':# insertion relative
            position = ordre
            latt = self._liste_ordonnee(sys=True)
            if not latt:
                ordreins = 1
            else:
                if ordre < 0:
                    position = len(latt)+1+ordre
                    if position < 0:
                        position = 0
                else:
                    position = ordre

                if position == 0:
                    ordreins = self.attributs[latt[0]].ordre/2.
                elif position >= len(latt):
                    ordreins = self.attributs[latt[-1]].ordre+1
#                        print ('ordrecalcule',ordreins,self.attributs[latt[-1]].ordre)
                else:
#                        print ('position intermediaire ',position,len(latt),latt)
                    precedent = int(position)
                    ordreins = (self.attributs[latt[precedent]].ordre+
                                self.attributs[latt[precedent+1]].ordre)/2.
        else:# insertion absolue$
#                print ('position absolue ',ordre)
            ordreins = ordre
            position = ordreins
        attr.ordre = ordreins



    def stocke_geometrie(self, type_geom, dimension=0, srid="3948", courbe=False, multiple=True):
        """stockage de la geometrie"""
#        print ("avant stockage geometrie ",self.info["nom_geometrie"],type_geom,
#               dimension,self.info["type_geom"])

        if isinstance(type_geom, (int, float)):
            type_geom = str(type_geom)
        if type_geom in TYPES_G:
            self.info["type_geom"] = type_geom
        elif type_geom in CODES_G:
            self.info["type_geom"] = CODES_G[type_geom]
        else:
            if type_geom:
                definition = type_geom.split(',')
            else:
                definition = ['alpha']
            if len(definition) > 1:
                srid = str(int(definition[1][:-1]))

            nom_type = definition[0]

            dimension = 3 if 'Z' in nom_type else dimension
            courbe = 'Curve' in nom_type
            multiple = 'Multi' in nom_type

            if 'Point' in nom_type:
                self.info["type_geom"] = '1'
            elif 'Surface' in nom_type or 'Polygon' in nom_type:
                self.info["type_geom"] = '3'
            elif 'Line' in nom_type or 'Curve' in nom_type:
                self.info["type_geom"] = '2'
            elif 'Geometry' in nom_type:
                self.info["type_geom"] = '-1'
            elif nom_type == 'alpha':
                self.info["type_geom"] = '0'
            elif nom_type.lower() == 'geometry' or nom_type.lower() == 'public.geometry':
#                print ('stocke_geom : classe ',self.nom, type_geom)
#                raise
                self.info["type_geom"] = '-1'
            else:
                print('schema:erreur type geometrique inconnu ->'+type_geom+'<-',
                      nom_type, self.groupe, self.nom, self.info["nom_geometrie"],
                      'non traite')
#                raise TypeError
                self.info["type_geom"] = '0'
        self.srid = srid
        self.multigeom = multiple
#        self.courbe = courbe
        if courbe:
            self.info['courbe'] = '1'
#        self.is_3d = dimension==3
        self.info["dimension"] = str(dimension)
#        print ("apres stockage geometrie ",self.info["nom_geometrie"],type_geom,
#               dimension, self.info["type_geom"])


    def ajout_attribut_modele(self, modele, nom=None, nom_court=None, force=False):
        ''' ajoute un attribut a partir d'un modele modele (surtout pour la filiation) '''
        if nom is None:
            nom = modele.nom
        if not force and nom in self.attributs:
            return self.attributs[nom]
        self.type_table = "i"
        self.changed = True
        attr = modele.copie(nom)
        ordre = attr.ordre
        self._gestion_ordre_insertion(attr, ordre)
        self.attributs[nom] = attr
        self._gestion_index(attr, attr.def_index)
        self._gestion_type_attribut(attr)
        self.liste_attributs_cache = []
        if nom_court is not None:
            self.attmap[nom_court] = nom
            if nom_court != nom:
                self.conversion_noms = True
        for i in self.fils:
            i.ajout_attribut_modele(modele, nom=nom)
        return self.attributs[nom]

    def ajout_attribut_tuple(self, definition):
        ''' ajoute un attribut a partir d'une requete base de donnnes
        ou d'un fichier descriptif csv ( en entree un namedtuple)'''

        self.type_table = "i"
        self.changed = True
        attr = None
        nom_attr = definition.nom_attr
        if nom_attr and nom_attr[0] == '#':
            raise KeyError('ajout attribut schema impossible '+nom_attr)
        if nom_attr in self.attributs:
            return self.attributs[nom_attr]
        type_attribut = definition.type_attribut
        if type_attribut == 'X':
            return # attribut non géré
        elif type_attribut in CODES_G:
            self.info["nom_geometrie"] = nom_attr
            self.stocke_geometrie(CODES_G[type_attribut], definition.dimension)

        elif 'geometry' in type_attribut.lower():
            self.info["nom_geometrie"] = nom_attr
            self.stocke_geometrie(type_attribut, definition.dimension)
        else: #self.liste_attributs.append(nom)
            self.liste_attributs_cache = []
            attr = A.Attribut(nom_attr, 0)
            self.attributs[nom_attr] = attr
#        print ('stocke:',attr,self.nom_geometrie)
        attr.ordre = definition.num_attribut
#        attr.type_att_base = type_attr_base
        attr.alias = definition.alias
        if attr.alias is None:
            attr.alias = ''
#            print ('stockage alias',self.identclasse, nom,alias,attr.alias)
        attr.taille = int(definition.taille) if definition.taille else 0
        attr.oblig = definition.obligatoire
        attr.multiple = definition.multiple
        attr.dec = definition.decimales
        attr.unique = definition.unique
#        if clef_primaire:
#            attr.clef_primaire = clef_primaire
        if definition.clef_etrangere:
            attr.clef_etrangere = definition.clef_etrangere+'.'+definition.cible_clef
        index = definition.index
        if index:
            aa_tmp = index.split(' ')
            for i in aa_tmp:
                bb_tmp = i.split(':')
                self.indexes[bb_tmp[0]] = bb_tmp[1]

        if type_attribut:
            self._gestion_type_attribut(attr, type_attribut, definition.defaut)

        for i in self.fils:
            i.ajout_attribut_modele(attr)

        return attr



    def _liste_ordonnee(self, sys=False):
        ''' retourne la liste des atttibuts tries selon leur ordre'''
        return sorted([i for i in self.attributs
                       if i[0] != '#' and (sys or not i.startswith('_sys_'))],
                      key=lambda k: self.attributs[k].ordre)




    def stocke_attribut(self, nom, type_attribut, defaut='', type_attr_base='T',
                        force=False, taille=0, dec=0, alias='', ordre=-1, mode_ordre='r',
                        nom_court='', clef_etr='', index='', dimension=0,
                        unique=False, obligatoire=False, multiple='non', nb_conf=0):
        """ stocke un attribut dans un schema """
        attr = None
        self.type_table = "i"
        self.changed = True
        if nom.startswith('#'):
            print("attention nom d'attribut incorrect : transformation", nom, '->', '_'+nom)
            nom = '_'+nom
#        print ('schema: stocke attribut',self.nom,nom,nom_court,type_attribut,ordre)
#        print ('schema: stocke attribut',self.nom,nom,type_attribut,ordre)
        if nom in self.attributs:
            if force:
#                print ('schema: stocke attribut: modif attribut ',
#                       self.nomschema,self.identclasse,nom)
                attr = self.attributs[nom]
            else:
                return self.attributs[nom]
        if type_attribut == 'X':
            return # attribut non géré
        elif type_attribut in TYPES_G:
            self.info["nom_geometrie"] = nom
            self.stocke_geometrie(type_attribut, dimension)
        elif type_attribut in CODES_G:
            self.info["nom_geometrie"] = nom
            self.stocke_geometrie(CODES_G[type_attribut], dimension)
#        elif nom.lower() =='geometrie': # c'est une description de geometrie
#            self.nom_geometrie=nom
#            self.stocke_geometrie(type_attribut,dimension)
        elif 'geometry' in type_attribut.lower():
            self.info["nom_geometrie"] = nom
#            print ('stockage attribut ',nom, type_attribut)
            self.stocke_geometrie(type_attribut, dimension)

        else: #self.liste_attributs.append(nom)
            self.liste_attributs_cache = []
            attr = A.Attribut(nom, nb_conf)
            if nom_court:
                self.attmap[nom_court] = nom
            if nom_court != nom:
                self.conversion_noms = True
#        print ('stocke:',attr,self.nom_geometrie)
        if attr:
            self._gestion_ordre_insertion(attr, ordre, mode_ordre)
            self.attributs[nom] = attr
            attr.type_att_base = type_attr_base
            attr.alias = alias if str(alias) != 'None' else ''
#            if self.identclasse[1]=='vl_sig_ems_doschant':
            attr.taille = taille
            attr.oblig = obligatoire
#            print ('stockage champ',self.identclasse, nom,ordre,position,
#                    attr.ordre,attr.oblig,obligatoire)

            attr.multiple = multiple == 'oui'
            attr.dec = dec
            attr.unique = unique
            if nom_court:
                attr.nom_court = nom_court


            if index:
                attr.index = index
                self._gestion_index(attr, index)

            if clef_etr:
                attr.clef_etr = clef_etr
                self._gestion_clef_etr(attr, clef_etr)

            if type_attribut:
#                print ('attribut entree_type', type_attribut)
                attr.type_att = type_attribut
                self._gestion_type_attribut(attr, type_attribut, defaut)

#            if attr.type_att=='A':
#                print ("type_attribut inconnu",self.nom,attr.nom,'-',type_attribut,
#                       attr.nom_conformite)
        for i in self.fils:
            i.stocke_attribut(nom, type_attribut, defaut=defaut,
                              type_attr_base=type_attr_base,
                              force=force, taille=taille, dec=dec,
                              alias=alias, ordre=attr.ordre, nom_court=nom_court, mode_ordre='a',
                              dimension=dimension, unique=unique, clef_etr=clef_etr, index=index,
                              obligatoire=obligatoire,
                              multiple=multiple)
        return attr
        # on transmet l'info a la descendance

    def get_liste_attributs(self, ordre='', liste=None, sys=False):
        '''recupere la liste des attributs dans l'ordre d'origine ou par ordre alpha'''
#        print("schema_interne:nombre d'attributs ", liste,self.liste_attributs_cache)
        #self.liste_attributs = list(self.attributs.keys())
        if self.liste_attributs_cache and self.ordrealpha == ordre:
            if liste:
                return [i for i in self.liste_attributs_cache if i in liste]
            return self.liste_attributs_cache[:]

        self.ordrealpha = ordre

        if ordre:
            #print ('schema : sortie liste ordre alpha')
            self.liste_attributs_cache = sorted([i for i in self.attributs
                                                 if i[0] != '#'
                                                 and (sys or not i.startswith('_sys_'))])
        else:
#            print ('schema : sortie liste ordre entree')
            self.liste_attributs_cache = self._liste_ordonnee(sys=sys)
#            print ('\n'.join([str((a.nom,a.ordre)) for a in self.attributs.values()]))
        if liste:
            return [i for i in self.liste_attributs_cache if i in liste]
        return self.liste_attributs_cache[:]



    def adapte_nom_court(self, nom_orig, taille):
        '''on essaye d'eviter les existants'''
        essai = 0
        repl = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        nom = nom_orig.upper()
        while nom in self.noms_courts and essai < 35:
            if len(nom) < taille:
                nom = nom+'1'
            else:
                nom = nom[:-1]+repl[essai]
            essai += 1
        if nom in self.noms_courts:
            print('echec raccourcissement', nom)
        self.noms_courts.add(nom)
        return nom

    def cree_noms_courts(self, longueur=10, abrev=None):
        '''genere des noms courts pour les sorties shape '''
        self.noms_courts = set()
        a_supp = 'YUOIAEBCDFGHJKLMNPQRSTVWXYZ0123456789'
        if abrev is None:
            abrev = self.schema.dic_abrev
        for i in self.attributs:
            att = self.attributs[i]
            if att.nom_court:
                self.noms_courts.add(att.nom_court.upper())
                continue
            nom = att.nom.upper()
#            nom1 = ""
            position = 0
            if len(nom) > longueur:
                nom = abrev.get(nom, nom)


            if len(nom) > longueur:
                parts = nom.split('_')
                if len(parts) > 2: # on essaye par blocs de 2
                    essai = '_'.join(parts[0:2])
                    essai = abrev.get(essai, essai)
                    nom = essai+"_"+'_'.join(parts[2:])
            if len(nom) > longueur:
                nom = '_'.join([abrev.get(i, i) for i in nom.split('_')])
            if len(nom) > longueur:
                nom = '_'.join([abrev.get(i, i) for i in nom.split('_')])

            if len(nom) > longueur:
                nom = re.sub("_([0-9])", r"\1", nom)
#            if len(nom) > longueur:
#                nom1 = nom
            while len(nom) > longueur:
                nom = nom.replace(a_supp[position], '')
                position = position+1
            nom = self.adapte_nom_court(nom, longueur)
#            if nom1:
#                print("raccourcissement force", att.nom, "->", nom1, "->", nom)

            att.nom_court = nom
